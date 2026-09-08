"""
模块名称: Cost Evaluator (成本评估引擎)
功能描述:
    评估 Agent 的运行成本：Token 消耗、API 调用费用、缓存节省率、人力替代比。
"""

from typing import Any, Dict, List

from src.evaluation.collector import AgentTrace
from src.services.logging import log_info


class CostEvaluator:
    """成本消耗评估器"""

    # 模型单价配置（美元 / 1K tokens）——可按实际供应商调整
    PRICE_TABLE = {
        "qwen-turbo": {"prompt": 0.0005, "completion": 0.0015},
        "qwen-plus": {"prompt": 0.002, "completion": 0.006},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gemini-pro": {"prompt": 0.0005, "completion": 0.0015},
        "default": {"prompt": 0.002, "completion": 0.006},
    }

    # 人力成本基准（每小时人民币，用于计算替代比）
    HUMAN_COST_PER_HOUR = 80.0
    HUMAN_TIME_PER_CASE_MINUTES = 20.0

    def evaluate(self, traces: List[AgentTrace]) -> Dict[str, Any]:
        """
        对多条 Trace 进行成本评估
        :param traces: AgentTrace 列表
        :return: 成本评估报告
        """
        if not traces:
            return {"error": "无Trace数据"}

        total_cost = 0.0
        total_tokens = {"prompt": 0, "completion": 0, "total": 0}
        total_retry_cost = 0.0
        cache_hits = 0

        for t in traces:
            cost, tokens = self._calc_single_cost(t)
            total_cost += cost
            for key in total_tokens:
                total_tokens[key] += tokens.get(key, 0)
            total_retry_cost += cost * t.retry_count
            if t.latency_ms < 500 and not t.rag_context:  # 启发式：低延迟且无RAG=可能命中缓存
                cache_hits += 1

        n = len(traces)
        avg_cost = total_cost / n
        human_cost = self._calc_human_cost(n)
        savings_rate = (human_cost - total_cost) / human_cost if human_cost > 0 else 0

        results = {
            "sample_count": n,
            "total_cost_usd": round(total_cost, 6),
            "avg_cost_per_case_usd": round(avg_cost, 6),
            "total_tokens": total_tokens,
            "avg_tokens_per_case": {
                "prompt": round(total_tokens["prompt"] / n, 2),
                "completion": round(total_tokens["completion"] / n, 2),
                "total": round(total_tokens["total"] / n, 2),
            },
            "retry_cost_usd": round(total_retry_cost, 6),
            "retry_cost_rate": round(total_retry_cost / total_cost, 4) if total_cost > 0 else 0,
            "cache_hits": cache_hits,
            "cache_hit_rate": round(cache_hits / n, 4),
            "human_cost_usd": round(human_cost, 2),
            "savings_rate": round(savings_rate, 4),
            "roi": round(savings_rate * 100, 2),
        }

        # 成本得分（越省钱分越高，但保底0分）
        # 基准：单次请求 $0.01 为满分，$0.1 为0分
        if avg_cost <= 0.005:
            score = 1.0
        elif avg_cost <= 0.01:
            score = 0.9
        elif avg_cost <= 0.03:
            score = 0.7
        elif avg_cost <= 0.05:
            score = 0.5
        else:
            score = max(0, 1 - avg_cost / 0.1)

        results["overall_score"] = round(score, 4)
        log_info(f"[CostEvaluator] 评估完成: 总成本 ${total_cost:.4f}, 节省率 {savings_rate:.1%}")
        return results

    def _calc_single_cost(self, trace: AgentTrace) -> tuple:
        """计算单条 Trace 的成本"""
        usage = trace.token_usage or {}
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        # 获取模型单价
        model = trace.model_name or "default"
        price = self.PRICE_TABLE.get(model, self.PRICE_TABLE["default"])

        prompt_cost = prompt_tokens / 1000 * price["prompt"]
        completion_cost = completion_tokens / 1000 * price["completion"]
        total_cost = prompt_cost + completion_cost

        return total_cost, {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total_tokens,
        }

    def _calc_human_cost(self, n_cases: int) -> float:
        """计算等效人力成本（美元）"""
        total_minutes = n_cases * self.HUMAN_TIME_PER_CASE_MINUTES
        total_hours = total_minutes / 60
        total_rmb = total_hours * self.HUMAN_COST_PER_HOUR
        # 粗略汇率：1 USD = 7.2 RMB
        return total_rmb / 7.2

    def estimate_monthly_savings(
        self,
        monthly_cases: int = 1000,
        avg_cost_per_case: float = None,
    ) -> Dict[str, Any]:
        """估算月度节省"""
        ai_cost = (avg_cost_per_case or 0.01) * monthly_cases
        human_cost = self._calc_human_cost(monthly_cases)
        savings = human_cost - ai_cost
        return {
            "monthly_cases": monthly_cases,
            "ai_cost_usd": round(ai_cost, 2),
            "human_cost_usd": round(human_cost, 2),
            "savings_usd": round(savings, 2),
            "savings_rate": round(savings / human_cost, 4) if human_cost > 0 else 0,
            "savings_human_hours": round(monthly_cases * self.HUMAN_TIME_PER_CASE_MINUTES / 60, 2),
        }
