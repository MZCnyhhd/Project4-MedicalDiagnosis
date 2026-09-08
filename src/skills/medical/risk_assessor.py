"""
模块名称: Risk Assessor Skill (风险评估技能)
功能描述:
    评估患者的整体健康风险和疾病预后。
"""

from src.skills.base import LLMSkill


class RiskAssessorSkill(LLMSkill):
    """风险评估技能"""

    def __init__(self):
        super().__init__(
            name="risk_assessor",
            description="基于患者年龄、基础疾病、生活方式等评估整体健康风险和疾病预后。",
            system_prompt=(
                "你是一位临床风险评估专家。请根据患者报告，完成以下评估：\n"
                "1. 识别主要危险因素（年龄、性别、吸烟、高血压、糖尿病、家族史等）\n"
                "2. 评估短期风险（30天内不良事件概率）\n"
                "3. 评估长期风险（1-5年并发症概率）\n"
                "4. 给出风险分层（低危/中危/高危/极高危）\n"
                "5. 提出风险干预建议"
            ),
            category="general",
        )
