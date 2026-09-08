"""
模块名称: Report Summarizer Skill (报告摘要技能)
功能描述:
    将冗长的患者报告提炼为结构化的医疗摘要。
"""

from src.skills.base import LLMSkill


class ReportSummarizerSkill(LLMSkill):
    """报告摘要技能"""

    def __init__(self):
        super().__init__(
            name="report_summarizer",
            description="将患者报告提炼为结构化的医疗摘要（主诉、现病史、既往史、检查、初步印象）。",
            system_prompt=(
                "你是一位医疗文书专家。请将以下患者报告提炼为结构化摘要，包含：\n"
                "- 主诉\n"
                "- 现病史（含起病时间、诱因、症状演变）\n"
                "- 既往史（含基础疾病、手术史、过敏史）\n"
                "- 重要阳性检查\n"
                "- 初步印象（3个最可能的诊断）"
            ),
            category="general",
        )
