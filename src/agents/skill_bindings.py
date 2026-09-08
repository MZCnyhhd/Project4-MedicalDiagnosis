"""
模块名称: Skill Bindings (技能绑定配置)
功能描述:
    定义各专科医生 Agent 默认绑定的技能列表。
    通过映射表实现专科与技能的按需组合。

用法示例:
    from src.agents.skill_bindings import get_skills_for_specialist
    from src.skills.registry import auto_register_skills

    auto_register_skills()
    agent = Agent(medical_report=report, role="心脏科医生")
    agent.bind_skills(get_skills_for_specialist("心脏科医生"))
    agent.execute_skills()
"""

from typing import List

# 专科 → 技能名称列表 的映射表
DEFAULT_SKILL_BINDINGS = {
    "心脏科医生": ["ecg_analysis", "risk_assessor", "symptom_checker"],
    "肺科医生": ["symptom_checker", "risk_assessor"],
    "内分泌科医生": ["symptom_checker", "risk_assessor"],
    "免疫科医生": ["symptom_checker", "risk_assessor"],
    "神经科医生": ["symptom_checker", "risk_assessor"],
    "消化科医生": ["symptom_checker", "risk_assessor"],
    "肾脏科医生": ["symptom_checker", "risk_assessor"],
    "精神科医生": ["symptom_checker", "report_summarizer"],
    "心理医生": ["symptom_checker", "report_summarizer"],
    "皮肤科医生": ["symptom_checker"],
    "肿瘤科医生": ["risk_assessor", "symptom_checker"],
    "血液科医生": ["symptom_checker", "risk_assessor"],
    "风湿科医生": ["symptom_checker", "risk_assessor"],
    # 默认绑定（未在表中定义的专科）
    "__default__": ["symptom_checker"],
}


def get_skills_for_specialist(specialist_name: str) -> List[str]:
    """
    获取指定专科医生默认绑定的技能列表。
    :param specialist_name: 专科名称
    :return: 技能名称列表
    """
    return DEFAULT_SKILL_BINDINGS.get(specialist_name, DEFAULT_SKILL_BINDINGS["__default__"])


def bind_skills_to_agent(agent) -> "Agent":
    """
    根据 Agent 的角色自动绑定对应的技能。
    :param agent: Agent 实例
    :return: 绑定后的 Agent 实例
    """
    skill_names = get_skills_for_specialist(agent.role)
    if skill_names:
        agent.bind_skills(skill_names)
    return agent
