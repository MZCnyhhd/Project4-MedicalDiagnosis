"""
模块名称: Skill Base (技能基类)
功能描述:
    定义 Skill 的抽象接口和通用行为。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseSkill(ABC):
    """
    技能基类。
    每个 Skill 代表一个原子化的诊断/分析能力。
    """

    def __init__(self, name: str, description: str, category: str = "general"):
        self.name = name
        self.description = description
        self.category = category

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> str:
        """
        执行技能。
        :param context: 上下文字典，通常包含 medical_report, extra_info, rag_context 等
        :return: 技能执行结果的文本描述
        """
        pass

    def get_prompt_fragment(self) -> str:
        """
        获取该技能在 Prompt 中的描述片段。
        用于在 Agent 提示词中声明可用技能。
        """
        return f"- {self.name}: {self.description}"

    def __repr__(self) -> str:
        return f"<Skill {self.name} ({self.category})>"


class LLMSkill(BaseSkill):
    """
    基于 LLM 调用的技能。
    通过构造特定 Prompt 调用大模型完成子任务。
    """

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        category: str = "llm",
    ):
        super().__init__(name, description, category)
        self.system_prompt = system_prompt

    def execute(self, context: Dict[str, Any]) -> str:
        from src.services.llm import get_chat_model
        model = get_chat_model()
        report = context.get("medical_report", "")
        full_prompt = f"{self.system_prompt}\n\n患者报告：{report}"
        try:
            response = model.invoke(full_prompt)
            return getattr(response, "content", str(response))
        except Exception as e:
            return f"[{self.name}] 执行失败: {str(e)}"


class ToolSkill(BaseSkill):
    """
    基于工具调用的技能。
    封装一个具体工具函数为 Skill 接口。
    """

    def __init__(
        self,
        name: str,
        description: str,
        tool_fn: callable,
        category: str = "tool",
    ):
        super().__init__(name, description, category)
        self.tool_fn = tool_fn

    def execute(self, context: Dict[str, Any]) -> str:
        try:
            result = self.tool_fn(context)
            return str(result)
        except Exception as e:
            return f"[{self.name}] 工具执行失败: {str(e)}"
