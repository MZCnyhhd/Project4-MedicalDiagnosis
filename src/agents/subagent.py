"""
模块名称: Subagent System (子智能体系统)
功能描述:
    为 Agent 提供层级化调用能力，支持父 Agent 动态委派任务给子 Agent。
    实现 Subagent 注册表、任务委派协议和层级诊断工作流。

设计理念:
    1.  **层级解耦**: 父 Agent 负责决策，Subagent 负责执行原子化子任务。
    2.  **动态组合**: Subagent 可在运行时按需注册和调用，非静态绑定。
    3.  **协议标准化**: 统一 `delegate(task, context)` 接口，屏蔽底层差异。

线程安全性:
    - Subagent 实例通常在父 Agent 的协程上下文中串行执行，无并发竞争。
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable

from src.agents.base import Agent, PROMPTS_CONFIG
from src.services.llm import get_chat_model
from src.services.logging import log_info, log_warn
from langchain_core.prompts import PromptTemplate


class Subagent(Agent):
    """
    子智能体。
    继承自 Agent，但专注于处理父 Agent 委派的单一子任务。
    可通过 `parent` 属性访问上级上下文。
    """

    def __init__(
        self,
        task_name: str,
        parent: Optional[Agent] = None,
        medical_report: str = None,
        role: str = None,
        extra_info: dict = None,
        rag_context: str = None,
    ):
        super().__init__(
            medical_report=medical_report,
            role=role or task_name,
            extra_info=extra_info,
            rag_context=rag_context,
        )
        self.task_name = task_name
        self.parent = parent
        self.subagents: Dict[str, "Subagent"] = {}

    def register_subagent(self, name: str, subagent: "Subagent") -> "Subagent":
        """注册下级子智能体，支持链式调用"""
        self.subagents[name] = subagent
        log_info(f"[Subagent] {self.task_name} 注册子智能体: {name}")
        return self

    async def delegate(self, name: str, task_input: str, extra_context: dict = None) -> str:
        """
        委派任务给指定子智能体。
        :param name: 子智能体名称
        :param task_input: 任务输入文本
        :param extra_context: 额外上下文
        :return: 子智能体输出
        """
        sub = self.subagents.get(name)
        if not sub:
            log_warn(f"[Subagent] 未找到子智能体 '{name}'，返回空结果")
            return f"[错误] 子智能体 {name} 未注册"
        # 注入父级上下文
        if extra_context:
            sub.extra_info = {**(sub.extra_info or {}), **extra_context}
        if task_input:
            sub.medical_report = task_input
        log_info(f"[Subagent] {self.task_name} → 委派任务至 {name}")
        return await sub.run_async()

    async def run_all_subagents(self, inputs: Dict[str, str]) -> Dict[str, str]:
        """
        并发执行所有已注册的子智能体。
        :param inputs: 子智能体名称到输入文本的映射
        :return: 子智能体名称到输出的映射
        """
        tasks = []
        names = []
        for name, inp in inputs.items():
            if name in self.subagents:
                tasks.append(self.delegate(name, inp))
                names.append(name)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        output = {}
        for name, res in zip(names, results):
            if isinstance(res, Exception):
                log_warn(f"[Subagent] {name} 执行异常: {res}")
                output[name] = f"[异常] {str(res)}"
            else:
                output[name] = res
        return output


class SubagentRegistry:
    """
    子智能体注册表。
    用于集中管理和按需创建 Subagent 实例（工厂模式）。
    """

    def __init__(self):
        self._factories: Dict[str, Callable[..., Subagent]] = {}

    def register(self, name: str, factory: Callable[..., Subagent]):
        """注册 Subagent 工厂函数"""
        self._factories[name] = factory
        log_info(f"[SubagentRegistry] 注册工厂: {name}")

    def create(self, name: str, **kwargs) -> Optional[Subagent]:
        """通过工厂创建 Subagent 实例"""
        factory = self._factories.get(name)
        if not factory:
            log_warn(f"[SubagentRegistry] 未找到工厂: {name}")
            return None
        return factory(**kwargs)

    def list_registered(self) -> List[str]:
        """列出已注册的 Subagent 名称"""
        return list(self._factories.keys())


class HierarchicalAgent(Subagent):
    """
    层级化智能体。
    具备自主规划能力：先分析任务，再决定调用哪些 Subagent，最后汇总结果。
    适用于 MDT 父 Agent、专科主任 Agent 等需要调度下属的场景。
    """

    def __init__(
        self,
        task_name: str,
        planner_prompt: str = None,
        parent: Optional[Agent] = None,
        medical_report: str = None,
        extra_info: dict = None,
        rag_context: str = None,
    ):
        super().__init__(
            task_name=task_name,
            parent=parent,
            medical_report=medical_report,
            role=task_name,
            extra_info=extra_info,
            rag_context=rag_context,
        )
        self.planner_prompt = planner_prompt or self._default_planner_prompt()
        self.model = get_chat_model()

    def _default_planner_prompt(self) -> str:
        return (
            "你是一位医疗任务调度专家。请根据患者报告，决定需要调用哪些子专家进行分析。"
            "已注册的子专家：{available_subagents}\n"
            "患者报告：{medical_report}\n"
            "请只输出一个 JSON 数组，包含需要调用的子专家名称字符串。"
            '例如：["心电图分析", "血液指标分析"]'
        )

    async def plan_and_execute(self) -> Dict[str, str]:
        """
        规划并执行：
        1. 调用 LLM 决定需要哪些 Subagent
        2. 并发执行这些 Subagent
        3. 返回汇总结果
        """
        if not self.subagents:
            log_warn(f"[HierarchicalAgent] {self.task_name} 无注册子智能体，直接执行自身")
            return {"self": await self.run_async()}

        # 步骤1：规划
        available = ", ".join(self.subagents.keys())
        plan_prompt = self.planner_prompt.format(
            available_subagents=available,
            medical_report=self.medical_report or "",
        )
        try:
            response = await self.model.ainvoke(plan_prompt)
            raw_text = getattr(response, "content", str(response))
            selected = self._parse_plan_json(raw_text)
        except Exception as e:
            log_warn(f"[HierarchicalAgent] 规划失败，降级为全量调用: {e}")
            selected = list(self.subagents.keys())

        # 过滤无效的子智能体
        selected = [s for s in selected if s in self.subagents]
        if not selected:
            selected = list(self.subagents.keys())

        log_info(f"[HierarchicalAgent] {self.task_name} 规划结果: {selected}")

        # 步骤2：并发执行
        inputs = {name: self.medical_report for name in selected}
        results = await self.run_all_subagents(inputs)
        return results

    @staticmethod
    def _parse_plan_json(raw_text: str) -> List[str]:
        """解析规划输出的 JSON 数组"""
        import json
        import re
        text = raw_text.strip()
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []
