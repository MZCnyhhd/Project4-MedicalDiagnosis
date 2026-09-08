"""
模块名称: Specialist Evaluator (专科诊断评估器)
功能描述:
    评估单个专科医生的诊断输出质量。
"""

from typing import Any

from tests.harness.base import BaseEvaluator, BaseMetric, MetricResult, TestCase
from tests.harness.metrics import KeywordOverlapMetric, JaccardSimilarityMetric
from src.agents.base import Agent


class SpecialistEvaluator(BaseEvaluator):
    """专科诊断质量评估器"""

    def __init__(self, specialist_name: str):
        self.specialist_name = specialist_name
        metrics = [
            KeywordOverlapMetric(name=f"{specialist_name}_keyword_overlap", threshold=0.3),
            JaccardSimilarityMetric(name=f"{specialist_name}_jaccard", threshold=0.1),
        ]
        super().__init__(f"specialist_{specialist_name}", metrics)

    async def run(self, case: TestCase) -> Any:
        agent = Agent(medical_report=case.report, role=self.specialist_name)
        result = await agent.run_async()
        return result

    def _extract_and_compute(self, metric: BaseMetric, raw_output: Any, case: TestCase) -> MetricResult:
        prediction = str(raw_output)
        if isinstance(metric, KeywordOverlapMetric):
            return metric.compute(prediction, case.expected_diagnoses)
        elif isinstance(metric, JaccardSimilarityMetric):
            # Jaccard 对比预测文本与真值诊断关键词拼接文本
            ground_truth_text = " ".join(case.expected_diagnoses)
            return metric.compute(prediction, ground_truth_text)
        return metric.compute(prediction, case.expected_diagnoses)
