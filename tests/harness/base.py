"""
模块名称: Harness Base (评估框架基类)
功能描述:
    定义评估框架的核心抽象：测试用例、评估指标、评估器、结果。
"""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class TestCase:
    """医疗诊断测试用例"""
    id: str
    name: str
    report: str
    expected_specialists: List[str] = field(default_factory=list)
    expected_entities: List[str] = field(default_factory=list)
    expected_diagnoses: List[str] = field(default_factory=list)
    expected_rag_sources: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            report=data.get("report", ""),
            expected_specialists=data.get("expected_specialists", []),
            expected_entities=data.get("expected_entities", []),
            expected_diagnoses=data.get("expected_diagnoses", []),
            expected_rag_sources=data.get("expected_rag_sources", []),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
        )


@dataclass
class MetricResult:
    """单个指标的评估结果"""
    metric_name: str
    score: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """单个评估器对单个用例的评估结果"""
    evaluator_name: str
    test_case_id: str
    passed: bool
    metrics: List[MetricResult] = field(default_factory=list)
    raw_output: Any = None
    latency_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluator_name": self.evaluator_name,
            "test_case_id": self.test_case_id,
            "passed": self.passed,
            "metrics": [asdict(m) for m in self.metrics],
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


class BaseMetric(ABC):
    """评估指标基类"""

    def __init__(self, name: str, threshold: float = 0.0):
        self.name = name
        self.threshold = threshold

    @abstractmethod
    def compute(self, prediction: Any, ground_truth: Any) -> MetricResult:
        """计算指标得分"""
        pass


class BaseEvaluator(ABC):
    """评估器基类"""

    def __init__(self, name: str, metrics: List[BaseMetric]):
        self.name = name
        self.metrics = metrics

    @abstractmethod
    async def run(self, case: TestCase) -> Any:
        """执行业务逻辑，返回待评估的原始输出"""
        pass

    async def evaluate(self, case: TestCase) -> EvalResult:
        """执行评估"""
        start = time.perf_counter()
        try:
            raw_output = await self.run(case)
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_results = []
            for metric in self.metrics:
                result = self._extract_and_compute(metric, raw_output, case)
                metrics_results.append(result)
            passed = all(
                m.score >= m.threshold if hasattr(m, 'threshold') else True
                for m in metrics_results
            )
            return EvalResult(
                evaluator_name=self.name,
                test_case_id=case.id,
                passed=passed,
                metrics=metrics_results,
                raw_output=raw_output,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return EvalResult(
                evaluator_name=self.name,
                test_case_id=case.id,
                passed=False,
                latency_ms=latency_ms,
                error=str(e),
            )

    @abstractmethod
    def _extract_and_compute(self, metric: BaseMetric, raw_output: Any, case: TestCase) -> MetricResult:
        """从原始输出中提取预测值并与真值对比"""
        pass


@dataclass
class HarnessReport:
    """完整评估报告"""
    total_cases: int
    results: List[EvalResult]
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "summary": self.summary,
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
