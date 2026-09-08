"""
模块名称: RAG Evaluator (检索质量评估器)
功能描述:
    评估 GraphRAG 的实体提取和上下文检索质量。
"""

from typing import Any, List

from tests.harness.base import BaseEvaluator, BaseMetric, MetricResult, TestCase
from tests.harness.metrics import EntityRecallMetric, RetrievalRecallMetric
from src.services.graph_rag import extract_medical_entities, retrieve_hybrid_knowledge_snippets


class RAGEvaluator(BaseEvaluator):
    """RAG 检索质量评估器"""

    def __init__(self):
        metrics = [
            EntityRecallMetric(name="entity_recall", threshold=0.5),
            RetrievalRecallMetric(name="retrieval_recall", threshold=0.3),
        ]
        super().__init__("rag", metrics)

    async def run(self, case: TestCase) -> Any:
        entities = extract_medical_entities(case.report)
        entity_names = [e.name for e in entities]
        context = retrieve_hybrid_knowledge_snippets(case.report)
        # 简单从上下文中提取可能引用的疾病名作为 source
        sources = self._extract_sources_from_context(context)
        return {
            "entities": entity_names,
            "sources": sources,
            "context_preview": context[:500] if context else "",
        }

    def _extract_and_compute(self, metric: BaseMetric, raw_output: Any, case: TestCase) -> MetricResult:
        if metric.name == "entity_recall":
            return metric.compute(raw_output["entities"], case.expected_entities)
        elif metric.name == "retrieval_recall":
            return metric.compute(raw_output["sources"], case.expected_rag_sources)
        return MetricResult(metric.name, 0.0)

    @staticmethod
    def _extract_sources_from_context(context: str) -> List[str]:
        """从上下文中粗略提取引用的疾病名称（简化处理）"""
        if not context:
            return []
        # 使用知识库中的疾病名作为候选
        known_diseases = [
            "冠心病", "心肌梗死", "高血压", "哮喘", "过敏性鼻炎", "花粉症",
            "糖尿病", "肾病综合征", "慢性肾病", "抑郁症", "焦虑症", "惊恐发作",
            "系统性红斑狼疮", "肾炎", "类风湿关节炎", "高脂血症",
            "心力衰竭", "心律失常", "胃溃疡", "肝炎", "肝硬化"
        ]
        found = [d for d in known_diseases if d in context]
        return found
