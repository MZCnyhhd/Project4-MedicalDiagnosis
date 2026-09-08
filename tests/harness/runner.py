"""
模块名称: Harness Runner (评估运行器)
功能描述:
    加载测试用例，调度多个评估器执行，汇总生成 HarnessReport。
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

from tests.harness.base import TestCase, HarnessReport, EvalResult, BaseEvaluator


class HarnessRunner:
    """评估运行器"""

    def __init__(self, cases_path: str = None):
        if cases_path is None:
            cases_path = os.path.join(os.path.dirname(__file__), "cases", "medical_cases.json")
        self.cases_path = cases_path
        self.cases: List[TestCase] = []
        self.evaluators: List[BaseEvaluator] = []

    def load_cases(self) -> "HarnessRunner":
        """加载测试用例"""
        with open(self.cases_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.cases = [TestCase.from_dict(item) for item in data]
        return self

    def register(self, evaluator: BaseEvaluator) -> "HarnessRunner":
        """注册评估器"""
        self.evaluators.append(evaluator)
        return self

    async def run(self) -> HarnessReport:
        """执行全部评估"""
        if not self.cases:
            self.load_cases()
        all_results: List[EvalResult] = []
        for case in self.cases:
            for evaluator in self.evaluators:
                result = await evaluator.evaluate(case)
                all_results.append(result)
        summary = self._build_summary(all_results)
        return HarnessReport(
            total_cases=len(self.cases),
            results=all_results,
            summary=summary,
        )

    def _build_summary(self, results: List[EvalResult]) -> Dict[str, Any]:
        """构建汇总统计"""
        summary = {
            "total_evaluations": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed and not r.error),
            "errors": sum(1 for r in results if r.error),
            "avg_latency_ms": round(sum(r.latency_ms for r in results) / len(results), 2) if results else 0.0,
        }
        # 按评估器分组统计
        by_evaluator: Dict[str, List[EvalResult]] = {}
        for r in results:
            by_evaluator.setdefault(r.evaluator_name, []).append(r)
        for name, eval_results in by_evaluator.items():
            summary[name] = {
                "count": len(eval_results),
                "passed": sum(1 for r in eval_results if r.passed),
                "avg_latency_ms": round(sum(r.latency_ms for r in eval_results) / len(eval_results), 2),
            }
            # 按指标汇总平均分
            metric_scores: Dict[str, List[float]] = {}
            for r in eval_results:
                for m in r.metrics:
                    metric_scores.setdefault(m.metric_name, []).append(m.score)
            summary[name]["metric_avgs"] = {
                k: round(sum(v) / len(v), 4) for k, v in metric_scores.items()
            }
        return summary
