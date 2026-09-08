"""
模块名称: Functional Evaluator (功能评估引擎)
功能描述:
    评估 Agent 的功能正确性：分诊准确率、诊断准确率、RAG命中率、MDT一致性。
    支持基于语义相似度的柔性匹配和 LLM-as-Judge 评审。
"""

import json
import re
from typing import Any, Dict, List, Optional

from src.evaluation.collector import AgentTrace
from src.services.llm import get_chat_model
from src.services.logging import log_info, log_warn


class FunctionalEvaluator:
    """功能正确性评估器"""

    def __init__(self, use_llm_judge: bool = True):
        self.use_llm_judge = use_llm_judge
        self.model = get_chat_model() if use_llm_judge else None

    async def evaluate(self, trace: AgentTrace, ground_truth: Optional[Dict] = None) -> Dict[str, Any]:
        """
        对单条 Trace 执行功能评估
        :param trace: Agent 执行追踪数据
        :param ground_truth: 标注真值（含 expected_specialists, expected_diagnoses 等）
        :return: 评估结果字典
        """
        results = {
            "trace_id": trace.trace_id,
            "overall_score": 0.0,
            "metrics": {},
        }

        if ground_truth:
            # 1. 分诊准确率
            if "expected_specialists" in ground_truth:
                results["metrics"]["triage_accuracy"] = self._eval_triage(
                    trace.triage_result, ground_truth["expected_specialists"]
                )

            # 2. 诊断准确率
            if "expected_diagnoses" in ground_truth:
                results["metrics"]["diagnosis_accuracy"] = await self._eval_diagnosis(
                    trace.mdt_output or trace.output_diagnosis,
                    ground_truth["expected_diagnoses"]
                )

            # 3. RAG 命中率
            if "expected_rag_sources" in ground_truth:
                results["metrics"]["rag_hit_rate"] = self._eval_rag_hit(
                    trace.rag_context, ground_truth["expected_rag_sources"]
                )

        # 4. MDT 一致性（无真值时检测专科意见冲突）
        results["metrics"]["mdt_consistency"] = self._eval_mdt_consistency(
            trace.specialist_outputs, trace.mdt_output
        )

        # 5. 幻觉检测
        results["metrics"]["hallucination_score"] = await self._detect_hallucination(trace)

        # 综合得分（加权平均）
        weights = {
            "triage_accuracy": 0.25,
            "diagnosis_accuracy": 0.35,
            "rag_hit_rate": 0.15,
            "mdt_consistency": 0.15,
            "hallucination_score": 0.10,
        }
        total_weight = 0
        weighted_sum = 0
        for key, weight in weights.items():
            if key in results["metrics"]:
                weighted_sum += results["metrics"][key].get("score", 0) * weight
                total_weight += weight
        results["overall_score"] = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0

        return results

    def _eval_triage(self, predicted: List[str], expected: List[str]) -> Dict[str, Any]:
        """评估分诊准确率（集合匹配）"""
        pred_set = set(s.lower() for s in predicted)
        exp_set = set(s.lower() for s in expected)
        tp = len(pred_set & exp_set)
        fp = len(pred_set - exp_set)
        fn = len(exp_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "score": f1,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "predicted": predicted,
            "expected": expected,
        }

    async def _eval_diagnosis(self, prediction: str, expected: List[str]) -> Dict[str, Any]:
        """评估诊断准确率（支持 LLM-as-Judge）"""
        if not self.model or not prediction:
            return {"score": 0, "method": "none", "reason": "无模型或无预测结果"}

        expected_text = "; ".join(expected)
        prompt = f"""你是一位严谨的医疗质量评审专家。请判断以下AI诊断与标准答案的一致性。

标准答案：{expected_text}
AI诊断：{prediction}

请从以下维度评分（0-10分）：
1. 主要疾病识别是否准确
2. 严重程度判断是否合理
3. 治疗建议是否恰当

只输出一个JSON对象：{{"score": 分数, "reason": "简要理由"}}
分数："""
        try:
            response = await self.model.ainvoke(prompt)
            raw = getattr(response, "content", str(response))
            match = re.search(r'\{[^}]+\}', raw)
            if match:
                result = json.loads(match.group())
                score = float(result.get("score", 0)) / 10.0
                return {
                    "score": round(score, 4),
                    "method": "llm_judge",
                    "reason": result.get("reason", ""),
                }
        except Exception as e:
            log_warn(f"[FunctionalEvaluator] LLM Judge 失败: {e}")

        # 降级：关键词匹配
        pred_lower = prediction.lower()
        hits = sum(1 for exp in expected if exp.lower() in pred_lower)
        score = hits / len(expected) if expected else 0
        return {"score": round(score, 4), "method": "keyword", "reason": "关键词匹配"}

    def _eval_rag_hit(self, rag_context: List[str], expected_sources: List[str]) -> Dict[str, Any]:
        """评估 RAG 检索命中率"""
        if not rag_context:
            return {"score": 0, "hit_count": 0, "total": len(expected_sources)}

        context_text = "\n".join(rag_context).lower()
        hits = 0
        for source in expected_sources:
            if source.lower() in context_text:
                hits += 1

        score = hits / len(expected_sources) if expected_sources else 0
        return {
            "score": round(score, 4),
            "hit_count": hits,
            "total": len(expected_sources),
        }

    def _eval_mdt_consistency(self, specialist_outputs: Dict[str, str], mdt_output: str) -> Dict[str, Any]:
        """评估 MDT 一致性：检测专科意见与最终诊断是否冲突"""
        if not specialist_outputs or not mdt_output:
            return {"score": 1.0, "conflicts": [], "reason": "无多专科输出"}

        conflicts = []
        mdt_lower = mdt_output.lower()

        for specialist, output in specialist_outputs.items():
            # 简单启发式：如果专科提到了某疾病但MDT未提及，可能为冲突
            # 实际生产环境应使用更复杂的语义匹配
            key_diseases = self._extract_diseases(output)
            for disease in key_diseases:
                if disease and disease not in mdt_lower:
                    conflicts.append({
                        "specialist": specialist,
                        "disease": disease,
                        "type": "mdt_missing",
                    })

        score = 1.0 if not conflicts else max(0, 1.0 - len(conflicts) * 0.2)
        return {
            "score": round(score, 4),
            "conflict_count": len(conflicts),
            "conflicts": conflicts[:5],  # 最多返回5条
        }

    async def _detect_hallucination(self, trace: AgentTrace) -> Dict[str, Any]:
        """幻觉检测：检测输出中是否存在与RAG上下文矛盾的信息"""
        if not self.model or not trace.rag_context or not trace.output_diagnosis:
            return {"score": 1.0, "method": "skip", "reason": "无条件检测"}

        context = "\n".join(trace.rag_context)[:2000]  # 截断避免过长
        prompt = f"""请判断以下AI诊断是否包含与医学知识库矛盾的内容（幻觉）。

医学知识库内容：
{context}

AI诊断：
{trace.output_diagnosis}

只输出JSON：{{"has_hallucination": true/false, "confidence": 0-1}}
"""
        try:
            response = await self.model.ainvoke(prompt)
            raw = getattr(response, "content", str(response))
            match = re.search(r'\{[^}]+\}', raw)
            if match:
                result = json.loads(match.group())
                has_hall = result.get("has_hallucination", False)
                conf = float(result.get("confidence", 0.5))
                # 分数越高表示幻觉越少（越安全）
                score = (1 - conf) if has_hall else 1.0
                return {
                    "score": round(score, 4),
                    "method": "llm_check",
                    "has_hallucination": has_hall,
                    "confidence": conf,
                }
        except Exception as e:
            log_warn(f"[FunctionalEvaluator] 幻觉检测失败: {e}")

        return {"score": 1.0, "method": "fallback", "reason": "检测失败，默认安全"}

    @staticmethod
    def _extract_diseases(text: str) -> List[str]:
        """从文本中提取疾病名称（简化版：匹配常见疾病后缀）"""
        patterns = [r'[\u4e00-\u9fa5]{2,}病', r'[\u4e00-\u9fa5]{2,}炎', r'[\u4e00-\u9fa5]{2,}癌', r'[\u4e00-\u9fa5]{2,}症']
        diseases = set()
        for pattern in patterns:
            for match in re.findall(pattern, text):
                diseases.add(match)
        return list(diseases)
