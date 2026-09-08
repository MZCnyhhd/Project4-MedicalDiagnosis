"""
模块名称: Symptom Checker Skill (症状核查技能)
功能描述:
    系统化梳理患者症状，按系统分类并评估紧急程度。
"""

from src.skills.base import LLMSkill


class SymptomCheckerSkill(LLMSkill):
    """症状核查技能"""

    def __init__(self):
        super().__init__(
            name="symptom_checker",
            description="系统化梳理患者症状，按系统分类并标记红旗症状（危急指征）。",
            system_prompt=(
                "你是一位症状分析专家。请仔细阅读患者报告，完成以下任务：\n"
                "1. 列出所有主观症状（患者自述）\n"
                "2. 列出所有客观体征（医生检查发现）\n"
                "3. 按系统分类（心血管/呼吸/消化/神经/内分泌等）\n"
                "4. 标记红旗症状（需要立即处理的危急指征）\n"
                "5. 给出症状严重度评估（轻/中/重/危急）"
            ),
            category="general",
        )
