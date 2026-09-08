"""
模块名称: Hierarchical MDT (层级化多学科团队)
功能描述:
    基于 Subagent 架构重构的 MDT 系统。
    MDT 父 Agent 不再平级并发所有专科，而是：
    1. 先由 MDT 父 Agent 分析病例并规划需要调用的专科 Subagent；
    2. 并发执行被选中的专科 Subagent；
    3. 专科 Subagent 内部可再委派细粒度子任务（如检查分析、症状分析）；
    4. 最终由 MDT 父 Agent 汇总所有子报告生成综合诊断。

设计理念:
    1.  **按需调度**: 避免不必要专科的调用，节省 Token 和延迟。
    2.  **层级透明**: 上游不感知下游的层级深度，只关心输入输出。
    3.  **向后兼容**: 保留原有 MDT 的 ReAct 综合能力，仅在调度层升级。
"""

from typing import Dict, Any, Optional

from src.agents.subagent import HierarchicalAgent, Subagent
from src.agents.base import PROMPTS_CONFIG
from src.services.logging import log_info, log_warn


class 层级化多学科团队(HierarchicalAgent):
    """
    层级化多学科团队（Hierarchical MDT）。
    继承自 HierarchicalAgent，具备自主规划 + Subagent 调度能力。
    """

    def __init__(
        self,
        medical_report: str = None,
        available_specialists: list[str] = None,
        rag_context: str = None,
    ):
        super().__init__(
            task_name="层级化多学科团队",
            medical_report=medical_report,
            extra_info={"available_specialists": available_specialists or []},
            rag_context=rag_context,
        )
        self.available_specialists = available_specialists or []
        # 将每个专科医生注册为 Subagent
        self._register_specialist_subagents()

    def _register_specialist_subagents(self):
        """将可用专科列表注册为 Subagent"""
        for specialist_name in self.available_specialists:
            sub = Subagent(
                task_name=specialist_name,
                parent=self,
                role=specialist_name,
                medical_report=self.medical_report,
                rag_context=self.rag_context,
            )
            self.register_subagent(specialist_name, sub)
        log_info(f"[层级化MDT] 已注册 {len(self.subagents)} 个专科 Subagent")

    async def run_hierarchical_diagnosis(self) -> str:
        """
        执行层级化诊断流程：
        1. plan_and_execute → 获取各专科 Subagent 报告
        2. 使用 ReAct 综合诊断（复用父类 MDT 能力）
        3. 返回 Markdown 格式的综合诊断
        """
        # 步骤1：规划并执行专科 Subagent
        specialist_reports = await self.plan_and_execute()
        valid_reports = {k: v for k, v in specialist_reports.items() if v and not v.startswith("[")}
        if not valid_reports:
            log_warn("[层级化MDT] 无有效专科报告，降级为直接诊断")
            return await self.run_async()

        log_info(f"[层级化MDT] 收到 {len(valid_reports)} 份有效专科报告，进入综合诊断")

        # 步骤2：综合诊断（复用原 MDT 的 ReAct 逻辑）
        self.extra_info = valid_reports
        self.prompt_template = self.create_prompt_template()
        final = await self.run_react_async()
        if not final:
            final = await self.run_async()
        return final

    def create_prompt_template(self):
        """复用原 MDT 的提示词模板构建逻辑"""
        activate_reports = []
        active_specialists = []
        reports = self.extra_info or {}
        for agent_name, report_content in reports.items():
            if report_content and report_content.strip():
                activate_reports.append(f"{agent_name}报告：{report_content}")
                active_specialists.append(agent_name)
        reports_text = "\n".join(activate_reports)
        specialists_text = "、".join(active_specialists)
        template_str = PROMPTS_CONFIG.get("multidisciplinary_team", "")
        if not template_str:
            template_str = (
                "请以多学科医疗团队的身份进行推理。"
                "你将获得以下专科医生提供的患者报告：{specialists_text}。"
                "任务：综合全部报告，列出 3 个可能的健康问题，并逐条说明对应理由与后续建议。"
                "输出格式：请使用 Markdown 格式输出。"
                "1. 使用三级标题（###）列出每个健康问题。"
                "2. 每个问题下使用无序列表（-）详细说明“理由”和“建议”。"
                "3. 确保排版整洁，易于阅读。\n\n{reports_text}"
            )
        from langchain_core.prompts import PromptTemplate
        return PromptTemplate.from_template(template_str).partial(
            specialists_text=specialists_text,
            reports_text=reports_text,
        )


def build_hierarchical_mdt(medical_report: str, rag_context: str = None) -> 层级化多学科团队:
    """
    工厂函数：快速构建一个包含所有专科的层级化 MDT。
    """
    specialist_prompts = PROMPTS_CONFIG.get("specialists", {})
    available = list(specialist_prompts.keys())
    if not available:
        available = [
            "心脏科医生", "心理医生", "精神科医生", "肺科医生", "神经科医生",
            "内分泌科医生", "免疫科医生", "消化科医生", "皮肤科医生",
            "肿瘤科医生", "血液科医生", "肾脏科医生", "风湿科医生"
        ]
    return 层级化多学科团队(
        medical_report=medical_report,
        available_specialists=available,
        rag_context=rag_context,
    )
