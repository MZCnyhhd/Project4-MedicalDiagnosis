"""
模块名称: Skill Registry (技能注册表)
功能描述:
    集中管理所有 Skill 的注册、查询和创建。
    采用单例模式，确保全局唯一注册表实例。
"""

from typing import Dict, List, Optional, Type

from src.skills.base import BaseSkill
from src.services.logging import log_info, log_warn


class SkillRegistry:
    """技能注册表（单例）"""

    _instance: Optional["SkillRegistry"] = None
    _skills: Dict[str, BaseSkill]

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
        return cls._instance

    def register(self, skill: BaseSkill) -> "SkillRegistry":
        """注册一个技能实例"""
        self._skills[skill.name] = skill
        log_info(f"[SkillRegistry] 注册技能: {skill.name} ({skill.category})")
        return self

    def get(self, name: str) -> Optional[BaseSkill]:
        """按名称获取技能"""
        skill = self._skills.get(name)
        if not skill:
            log_warn(f"[SkillRegistry] 未找到技能: {name}")
        return skill

    def list_skills(self, category: str = None) -> List[str]:
        """列出已注册的技能名称"""
        if category:
            return [k for k, v in self._skills.items() if v.category == category]
        return list(self._skills.keys())

    def get_by_category(self, category: str) -> List[BaseSkill]:
        """按类别获取技能列表"""
        return [v for v in self._skills.values() if v.category == category]

    def unregister(self, name: str) -> bool:
        """注销技能"""
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def clear(self):
        """清空所有技能"""
        self._skills.clear()


def auto_register_skills():
    """
    自动注册项目中预定义的医疗技能。
    在应用启动时调用一次即可。
    """
    from src.skills.medical.ecg_analysis import ECGAnalysisSkill
    from src.skills.medical.symptom_checker import SymptomCheckerSkill
    from src.skills.medical.report_summarizer import ReportSummarizerSkill
    from src.skills.medical.risk_assessor import RiskAssessorSkill

    registry = SkillRegistry()
    registry.register(ECGAnalysisSkill())
    registry.register(SymptomCheckerSkill())
    registry.register(ReportSummarizerSkill())
    registry.register(RiskAssessorSkill())
    log_info(f"[SkillRegistry] 自动注册完成，共 {len(registry.list_skills())} 个技能")
