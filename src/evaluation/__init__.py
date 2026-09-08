"""
模块名称: Agent Evaluation System (智能体评估系统)
功能描述:
    为医疗诊断 AI 智能体提供全链路、多维度的运行时评估能力。
    覆盖功能正确性、性能效率、成本消耗、医疗安全四大维度。

设计理念:
    1. 无侵入采集：通过 Trace 机制记录 Agent 执行全链路，不修改业务核心逻辑。
    2. 多维度评估：功能、性能、成本、安全独立评估，可自由组合。
    3. 实时+离线双模：既支持线上实时监控，也支持批量离线回归测试。

依赖关系:
    - tests.harness.base: 复用现有 Harness 的测试用例与指标抽象
    - src.services.llm: 用于 LLM-as-Judge 评估
"""

from src.evaluation.orchestrator import EvaluationOrchestrator
from src.evaluation.collector import AgentTrace, TraceCollector
from src.evaluation.report import EvaluationReport

__all__ = [
    "EvaluationOrchestrator",
    "AgentTrace",
    "TraceCollector",
    "EvaluationReport",
]
