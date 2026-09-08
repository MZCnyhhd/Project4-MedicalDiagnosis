"""
模块名称: MDT Evaluator (综合诊断评估器)
功能描述:
    评估多学科团队（MDT）最终综合诊断的质量。
"""

from typing import Any

from tests.harness.base import BaseEvaluator, BaseMetric, MetricResult, TestCase
from tests.harness.metrics import KeywordOverlapMetric, JaccardSimilarityMetric
from src.agents.base import 多学科团队


class MDTEvaluator(BaseEvaluator):
    """MDT 综合诊断质量评估器"""

    def __init__(self):
        metrics = [
            KeywordOverlapMetric(name="mdt_keyword_overlap", threshold=0.4),
            JaccardSimilarityMetric(name="mdt_jaccard", threshold=0.15),
        ]
        super().__init__("mdt", metrics)

    async def run(self, case: TestCase) -> Any:
        # 构建模拟的专科报告（简化为用真值构造，实际可用 SpecialistEvaluator 的输出）
        mock_reports = {}
        for specialist in case.expected_specialists:
            mock_reports[specialist] = f"{specialist}诊断：考虑{', '.join(case.expected_diagnoses)}。"
        team = 多学科团队(reports=mock_reports)
        # 优先使用 ReAct，降级使用普通模式
        result = await team.run_react_async()
        if not result:
            result = await team.run_async()
        return result

    def _extract_and_compute(self, metric: BaseMetric, raw_output: Any, case: TestCase) -> MetricResult:
        prediction = str(raw_output)
        if isinstance(metric, KeywordOverlapMetric):
            return metric.compute(prediction, case.expected_diagnoses)
        elif isinstance(metric, JaccardSimilarityMetric):
            ground_truth_text = " ".join(case.expected_diagnoses)
            return metric.compute(prediction, ground_truth_text)
        return metric.compute(prediction, case.expected_diagnoses)
