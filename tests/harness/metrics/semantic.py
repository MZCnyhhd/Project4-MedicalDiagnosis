"""
模块名称: Semantic Metrics (语义指标)
功能描述:
    基于关键词重叠和 Jaccard 相似度的轻量级语义评估。
    如需更精确的语义相似度，可在此扩展 Embedding Cosine 相似度。
"""

import re
from typing import Any, List

from tests.harness.base import BaseMetric, MetricResult


def _tokenize(text: str) -> set:
    """简单的中文/英文分词：按非字母数字汉字切分"""
    tokens = re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", text.lower())
    return set(tokens)


class KeywordOverlapMetric(BaseMetric):
    """关键词重叠率（基于真值关键词在预测文本中的出现情况）"""

    def __init__(self, name: str = "keyword_overlap", threshold: float = 0.0):
        super().__init__(name, threshold)

    def compute(self, prediction: str, ground_truth_keywords: List[str]) -> MetricResult:
        if not ground_truth_keywords:
            return MetricResult(self.name, 1.0)
        pred_lower = prediction.lower()
        matched = [kw for kw in ground_truth_keywords if kw.lower() in pred_lower]
        score = len(matched) / len(ground_truth_keywords)
        return MetricResult(self.name, score, {"matched_keywords": matched, "total_keywords": len(ground_truth_keywords)})


class JaccardSimilarityMetric(BaseMetric):
    """Jaccard 文本相似度"""

    def __init__(self, name: str = "jaccard_similarity", threshold: float = 0.0):
        super().__init__(name, threshold)

    def compute(self, prediction: str, ground_truth: str) -> MetricResult:
        pred_tokens = _tokenize(prediction)
        gt_tokens = _tokenize(ground_truth)
        if not pred_tokens and not gt_tokens:
            return MetricResult(self.name, 1.0)
        intersection = len(pred_tokens & gt_tokens)
        union = len(pred_tokens | gt_tokens)
        score = intersection / union if union > 0 else 0.0
        return MetricResult(self.name, score)
