"""
模块名称: ECG Analysis Skill (心电图分析技能)
功能描述:
    从患者报告中提取心电图相关信息并给出分析建议。
"""

from src.skills.base import LLMSkill


class ECGAnalysisSkill(LLMSkill):
    """心电图分析技能"""

    def __init__(self):
        super().__init__(
            name="ecg_analysis",
            description="分析患者心电图检查结果，识别心律失常、心肌缺血、心肌梗死等异常。",
            system_prompt=(
                "你是一位心电图分析专家。请从患者报告中提取所有心电图相关数据（如导联、ST段、T波、QRS波群等），"
                "并给出专业分析：\n"
                "1. 列出心电图异常发现\n"
                "2. 判断可能的心脏问题\n"
                "3. 给出下一步建议"
            ),
            category="cardiology",
        )
