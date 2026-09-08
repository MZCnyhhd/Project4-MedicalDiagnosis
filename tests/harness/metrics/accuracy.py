"""
模块名称: Accuracy Metrics (准确率指标)
功能描述:
    精确匹配、召回率、F1 等基础指标。
"""

from typing import Any, List

from tests.harness.base import BaseMetric, MetricResult


class ExactMatchMetric(BaseMetric):
    """精确匹配指标（用于列表元素匹配）"""

    def __init__(self, name: str = "exact_match", threshold: float = 0.0):
        super().__init__(name, threshold)

    def compute(self, prediction: List[str], ground_truth: List[str]) -> MetricResult:
        if not ground_truth:
            score = 1.0 if not prediction else 0.0
            return MetricResult(self.name, score, {"prediction": prediction, "ground_truth": ground_truth})
        pred_set = set(prediction)
        gt_set = set(ground_truth)
        score = len(pred_set & gt_set) / len(gt_set)
        return MetricResult(
            self.name,
            score,
            {"matched": list(pred_set & gt_set), "missing": list(gt_set - pred_set), "extra": list(pred_set - gt_set)},
        )


class RecallMetric(BaseMetric):
    """召回率指标"""

    def __init__(self, name: str = "recall", threshold: float = 0.0):
        super().__init__(name, threshold)

    def compute(self, prediction: List[str], ground_truth: List[str]) -> MetricResult:
        if not ground_truth:
            score = 1.0 if not prediction else 0.0
            return MetricResult(self.name, score)
        pred_set = set(prediction)
        gt_set = set(ground_truth)
        score = len(pred_set & gt_set) / len(gt_set)
        return MetricResult(self.name, score)


class F1Metric(BaseMetric):
    """F1 指标"""

    def __init__(self, name: str = "f1", threshold: float = 0.0):
        super().__init__(name, threshold)

    def compute(self, prediction: List[str], ground_truth: List[str]) -> MetricResult:
        pred_set = set(prediction)
        gt_set = set(ground_truth)
        if not pred_set and not gt_set:
            return MetricResult(self.name, 1.0)
        tp = len(pred_set & gt_set)
        precision = tp / len(pred_set) if pred_set else 0.0
        recall = tp / len(gt_set) if gt_set else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return MetricResult(self.name, f1, {"precision": precision, "recall": recall})
