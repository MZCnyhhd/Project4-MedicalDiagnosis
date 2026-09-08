"""
模块名称: Performance Evaluator (性能评估引擎)
功能描述:
    评估 Agent 的性能效率：端到端延迟、RAG检索耗时、并发吞吐、流式输出间隔。
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
import numpy as np

from src.evaluation.collector import AgentTrace
from src.services.logging import log_info


class PerformanceEvaluator:
    """性能效率评估器"""

    # 性能阈值配置（单位：毫秒）
    THRESHOLDS = {
        "end_to_end_latency": 4000,    # 4秒
        "rag_latency": 500,            # 500ms
        "llm_first_token": 2000,       # 2秒
        "inter_chunk_gap": 300,        # 300ms
    }

    def evaluate(self, traces: List[AgentTrace]) -> Dict[str, Any]:
        """
        对多条 Trace 进行性能评估
        :param traces: AgentTrace 列表
        :return: 性能评估报告
        """
        if not traces:
            return {"error": "无Trace数据"}

        latencies = [t.latency_ms for t in traces]
        rag_latencies = [t.rag_latency_ms for t in traces if t.rag_latency_ms > 0]

        results = {
            "sample_count": len(traces),
            "end_to_end_latency": self._compute_latency_stats(latencies),
            "rag_latency": self._compute_latency_stats(rag_latencies) if rag_latencies else None,
            "throughput_qps": self._estimate_throughput(traces),
            "threshold_violations": self._count_violations(traces),
        }

        # 综合性能得分（P95延迟越短得分越高）
        p95 = results["end_to_end_latency"]["p95"]
        if p95 <= 1000:
            score = 1.0
        elif p95 <= 3000:
            score = 0.9
        elif p95 <= 4000:
            score = 0.7
        elif p95 <= 6000:
            score = 0.5
        else:
            score = max(0, 1 - p95 / 20000)

        results["overall_score"] = round(score, 4)
        return results

    def _compute_latency_stats(self, values: List[float]) -> Dict[str, float]:
        """计算延迟统计量"""
        arr = np.array(values)
        return {
            "min_ms": round(float(np.min(arr)), 2),
            "max_ms": round(float(np.max(arr)), 2),
            "mean_ms": round(float(np.mean(arr)), 2),
            "median_ms": round(float(np.median(arr)), 2),
            "p50_ms": round(float(np.percentile(arr, 50)), 2),
            "p95_ms": round(float(np.percentile(arr, 95)), 2),
            "p99_ms": round(float(np.percentile(arr, 99)), 2),
            "std_ms": round(float(np.std(arr)), 2),
        }

    def _estimate_throughput(self, traces: List[AgentTrace]) -> Dict[str, float]:
        """估算吞吐量（基于时间窗口内的请求数）"""
        if len(traces) < 2:
            return {"qps": 0, "window_seconds": 0}

        timestamps = sorted([t.timestamp for t in traces])
        window = timestamps[-1] - timestamps[0]
        qps = len(traces) / window if window > 0 else 0
        return {
            "qps": round(qps, 4),
            "window_seconds": round(window, 2),
            "total_requests": len(traces),
        }

    def _count_violations(self, traces: List[AgentTrace]) -> Dict[str, Any]:
        """统计阈值违规情况"""
        violations = {
            "end_to_end_over_4s": 0,
            "rag_over_500ms": 0,
            "total": 0,
        }
        for t in traces:
            if t.latency_ms > self.THRESHOLDS["end_to_end_latency"]:
                violations["end_to_end_over_4s"] += 1
            if t.rag_latency_ms > self.THRESHOLDS["rag_latency"]:
                violations["rag_over_500ms"] += 1

        violations["total"] = violations["end_to_end_over_4s"] + violations["rag_over_500ms"]
        violations["violation_rate"] = round(violations["total"] / max(len(traces) * 2, 1), 4)
        return violations

    async def benchmark_concurrent(
        self,
        test_func,
        n_requests: int = 100,
        concurrency: int = 10,
    ) -> Dict[str, Any]:
        """
        并发压测工具
        :param test_func: 异步测试函数，接收一个参数并返回结果
        :param n_requests: 总请求数
        :param concurrency: 并发数
        :return: 压测报告
        """
        semaphore = asyncio.Semaphore(concurrency)
        latencies: List[float] = []
        errors: List[str] = []

        async def _run_single(idx: int):
            async with semaphore:
                start = time.perf_counter()
                try:
                    await test_func(idx)
                except Exception as e:
                    errors.append(str(e))
                finally:
                    lat = (time.perf_counter() - start) * 1000
                    latencies.append(lat)

        start_all = time.perf_counter()
        await asyncio.gather(*[_run_single(i) for i in range(n_requests)])
        total_time = (time.perf_counter() - start_all) * 1000

        arr = np.array(latencies)
        report = {
            "n_requests": n_requests,
            "concurrency": concurrency,
            "total_time_ms": round(total_time, 2),
            "qps": round(n_requests / (total_time / 1000), 4) if total_time > 0 else 0,
            "latency": {
                "min_ms": round(float(np.min(arr)), 2),
                "max_ms": round(float(np.max(arr)), 2),
                "mean_ms": round(float(np.mean(arr)), 2),
                "p50_ms": round(float(np.percentile(arr, 50)), 2),
                "p95_ms": round(float(np.percentile(arr, 95)), 2),
                "p99_ms": round(float(np.percentile(arr, 99)), 2),
            },
            "error_count": len(errors),
            "error_rate": round(len(errors) / n_requests, 4),
        }
        log_info(f"[PerformanceEvaluator] 压测完成: {n_requests}请求, {report['qps']:.2f} QPS")
        return report
