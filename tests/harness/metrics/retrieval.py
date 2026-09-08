"""
模块名称: Retrieval Metrics (检索指标)
功能描述:
    评估 RAG 检索和实体提取的召回率。
"""

from typing import Any, List

from tests.harness.base import BaseMetric, MetricResult


class EntityRecallMetric(BaseMetric):
    """实体提取召回率"""

    def __init__(self, name: str = "entity_recall", threshold: float = 0.0):
        super().__init__(name, threshold)

    def compute(self, prediction: List[str], ground_truth: List[str]) -> MetricResult:
        if not ground_truth:
            score = 1.0 if not prediction else 0.0
            return MetricResult(self.name, score)
        pred_set = set(prediction)
        gt_set = set(ground_truth)
        matched = pred_set & gt_set
        score = len(matched) / len(gt_set)
        return MetricResult(
            self.name,
            score,
            {"matched": list(matched), "missing": list(gt_set - pred_set)},
        )


class RetrievalRecallMetric(BaseMetric):
    """检索结果召回率（评估 RAG 返回的 source 是否覆盖预期来源）"""

    def __init__(self, name: str = "retrieval_recall", threshold: float = 0.0):
        super().__init__(name, threshold)

    def compute(self, prediction_sources: List[str], ground_truth_sources: List[str]) -> MetricResult:
        if not ground_truth_sources:
            score = 1.0 if not prediction_sources else 0.0
            return MetricResult(self.name, score)
        pred_set = set(prediction_sources)
        gt_set = set(ground_truth_sources)
        matched = pred_set & gt_set
        score = len(matched) / len(gt_set)
        return MetricResult(
            self.name,
            score,
            {"matched_sources": list(matched), "missing_sources": list(gt_set - pred_set)},
        )
