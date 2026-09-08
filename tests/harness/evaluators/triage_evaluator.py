"""
模块名称: Triage Evaluator (分诊评估器)
功能描述:
    评估智能分诊模块是否正确选择了相关专科医生。
"""

from typing import Any

from tests.harness.base import BaseEvaluator, BaseMetric, MetricResult, TestCase, EvalResult
from tests.harness.metrics import ExactMatchMetric, RecallMetric
from src.core.triage import triage_specialists


class TriageEvaluator(BaseEvaluator):
    """分诊质量评估器"""

    def __init__(self):
        metrics = [
            ExactMatchMetric(name="triage_exact_match", threshold=0.5),
            RecallMetric(name="triage_recall", threshold=0.5),
        ]
        super().__init__("triage", metrics)

    async def run(self, case: TestCase) -> Any:
        available_specialists = [
            "心脏科医生", "心理医生", "精神科医生", "肺科医生", "神经科医生",
            "内分泌科医生", "免疫科医生", "消化科医生", "皮肤科医生",
            "肿瘤科医生", "血液科医生", "肾脏科医生", "风湿科医生"
        ]
        selected = await triage_specialists(case.report, available_specialists)
        return selected

    def _extract_and_compute(self, metric: BaseMetric, raw_output: Any, case: TestCase) -> MetricResult:
        prediction = raw_output
        ground_truth = case.expected_specialists
        return metric.compute(prediction, ground_truth)
