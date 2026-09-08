"""
模块名称: Evaluation Orchestrator (评估协调器)
功能描述:
    协调四大评估引擎，支持实时评估与离线批量评估。
    提供统一的评估入口和综合报告聚合。
"""

import time
import json
from typing import Any, Dict, List, Optional

from src.evaluation.collector import AgentTrace, TraceCollector
from src.evaluation.functional import FunctionalEvaluator
from src.evaluation.performance import PerformanceEvaluator
from src.evaluation.cost import CostEvaluator
from src.evaluation.safety import SafetyEvaluator
from src.evaluation.report import EvaluationReport
from src.services.logging import log_info, log_warn


class EvaluationOrchestrator:
    """评估协调器"""

    def __init__(
        self,
        use_llm_judge: bool = True,
        functional_enabled: bool = True,
        performance_enabled: bool = True,
        cost_enabled: bool = True,
        safety_enabled: bool = True,
    ):
        self.collector = TraceCollector()
        self.functional = FunctionalEvaluator(use_llm_judge=use_llm_judge) if functional_enabled else None
        self.performance = PerformanceEvaluator() if performance_enabled else None
        self.cost = CostEvaluator() if cost_enabled else None
        self.safety = SafetyEvaluator(use_llm_judge=use_llm_judge) if safety_enabled else None

        self._enabled = {
            "functional": functional_enabled,
            "performance": performance_enabled,
            "cost": cost_enabled,
            "safety": safety_enabled,
        }

    async def evaluate_single(
        self,
        trace: AgentTrace,
        ground_truth: Optional[Dict] = None,
    ) -> EvaluationReport:
        """
        对单条 Trace 执行完整评估
        :param trace: Agent 执行追踪数据
        :param ground_truth: 可选的标注真值
        :return: 综合评估报告
        """
        start = time.perf_counter()
        results = {}

        if self.functional:
            try:
                results["functional"] = await self.functional.evaluate(trace, ground_truth)
            except Exception as e:
                log_warn(f"[Orchestrator] 功能评估失败: {e}")
                results["functional"] = {"error": str(e)}

        if self.safety:
            try:
                results["safety"] = await self.safety.evaluate(trace)
            except Exception as e:
                log_warn(f"[Orchestrator] 安全评估失败: {e}")
                results["safety"] = {"error": str(e)}

        # 性能与成本评估需要多条Trace，单条时跳过或简化
        latency_ms = (time.perf_counter() - start) * 1000
        report = EvaluationReport(
            trace_id=trace.trace_id,
            timestamp=time.time(),
            results=results,
            latency_ms=latency_ms,
        )
        return report

    async def evaluate_batch(
        self,
        traces: List[AgentTrace],
        ground_truths: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        对多条 Trace 执行批量评估
        :param traces: AgentTrace 列表
        :param ground_truths: 可选的标注真值列表（与traces一一对应）
        :return: 批量综合评估报告
        """
        if not traces:
            return {"error": "无Trace数据"}

        start = time.perf_counter()
        n = len(traces)
        log_info(f"[Orchestrator] 开始批量评估: {n} 条Trace")

        # 1. 功能评估（逐条）
        functional_results = []
        if self.functional:
            for i, trace in enumerate(traces):
                gt = ground_truths[i] if ground_truths and i < len(ground_truths) else None
                try:
                    result = await self.functional.evaluate(trace, gt)
                    functional_results.append(result)
                except Exception as e:
                    log_warn(f"[Orchestrator] Trace {trace.trace_id[:8]} 功能评估失败: {e}")

        # 2. 性能评估（批量）
        performance_result = None
        if self.performance:
            try:
                performance_result = self.performance.evaluate(traces)
            except Exception as e:
                log_warn(f"[Orchestrator] 性能评估失败: {e}")

        # 3. 成本评估（批量）
        cost_result = None
        if self.cost:
            try:
                cost_result = self.cost.evaluate(traces)
            except Exception as e:
                log_warn(f"[Orchestrator] 成本评估失败: {e}")

        # 4. 安全评估（逐条）
        safety_results = []
        if self.safety:
            for trace in traces:
                try:
                    result = await self.safety.evaluate(trace)
                    safety_results.append(result)
                except Exception as e:
                    log_warn(f"[Orchestrator] Trace {trace.trace_id[:8]} 安全评估失败: {e}")

        # 聚合报告
        latency_ms = (time.perf_counter() - start) * 1000
        report = self._aggregate_report(
            traces=traces,
            functional_results=functional_results,
            performance_result=performance_result,
            cost_result=cost_result,
            safety_results=safety_results,
            latency_ms=latency_ms,
        )
        log_info(f"[Orchestrator] 批量评估完成: 耗时 {latency_ms:.0f}ms")
        return report

    def evaluate_recent_traces(self, n: int = 100) -> Dict[str, Any]:
        """对最近n条Trace执行批量评估（同步入口）"""
        traces = self.collector.get_recent_traces(n)
        if not traces:
            return {"error": "无历史Trace数据"}
        # 异步执行
        import asyncio
        return asyncio.run(self.evaluate_batch(traces))

    def _aggregate_report(
        self,
        traces: List[AgentTrace],
        functional_results: List[Dict],
        performance_result: Optional[Dict],
        cost_result: Optional[Dict],
        safety_results: List[Dict],
        latency_ms: float,
    ) -> Dict[str, Any]:
        """聚合四大维度评估结果"""
        # 功能得分
        func_scores = [r.get("overall_score", 0) for r in functional_results if "overall_score" in r]
        avg_func_score = sum(func_scores) / len(func_scores) if func_scores else 0

        # 安全得分
        safety_scores = [r.get("overall_score", 0) for r in safety_results if "overall_score" in r]
        avg_safety_score = sum(safety_scores) / len(safety_scores) if safety_scores else 0

        # 性能得分
        perf_score = performance_result.get("overall_score", 0) if performance_result else 0

        # 成本得分
        cost_score = cost_result.get("overall_score", 0) if cost_result else 0

        # 加权综合得分
        weights = {
            "functional": 0.35,
            "performance": 0.25,
            "cost": 0.15,
            "safety": 0.25,
        }
        overall = (
            avg_func_score * weights["functional"] +
            perf_score * weights["performance"] +
            cost_score * weights["cost"] +
            avg_safety_score * weights["safety"]
        )

        return {
            "version": "1.0",
            "timestamp": time.time(),
            "sample_count": len(traces),
            "eval_latency_ms": round(latency_ms, 2),
            "overall_score": round(overall, 4),
            "dimension_scores": {
                "functional": round(avg_func_score, 4),
                "performance": round(perf_score, 4),
                "cost": round(cost_score, 4),
                "safety": round(avg_safety_score, 4),
            },
            "details": {
                "functional": functional_results,
                "performance": performance_result,
                "cost": cost_result,
                "safety": safety_results,
            },
            "summary": self._generate_summary(
                avg_func_score, perf_score, cost_score, avg_safety_score, overall
            ),
        }

    def _generate_summary(
        self,
        func: float,
        perf: float,
        cost: float,
        safety: float,
        overall: float,
    ) -> Dict[str, str]:
        """生成评估总结"""
        def _grade(score: float) -> str:
            if score >= 0.9:
                return "优秀"
            elif score >= 0.8:
                return "良好"
            elif score >= 0.6:
                return "及格"
            else:
                return "需改进"

        return {
            "overall": f"综合评分 {overall:.2f}（{_grade(overall)}）",
            "functional": f"功能正确性 {func:.2f}（{_grade(func)}）",
            "performance": f"性能效率 {perf:.2f}（{_grade(perf)}）",
            "cost": f"成本控制 {cost:.2f}（{_grade(cost)}）",
            "safety": f"安全合规 {safety:.2f}（{_grade(safety)}）",
        }
