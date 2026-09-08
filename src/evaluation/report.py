"""
模块名称: Evaluation Report (评估报告)
功能描述:
    定义评估报告的数据结构和序列化方法。
    支持 JSON、Markdown、HTML 多种格式输出。
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationReport:
    """单条Trace的评估报告"""
    trace_id: str
    timestamp: float
    results: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "latency_ms": self.latency_ms,
            "results": self.results,
            "error": self.error,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class ReportFormatter:
    """报告格式化器"""

    @staticmethod
    def to_markdown(report: Dict[str, Any]) -> str:
        """将批量评估报告转为 Markdown"""
        lines = [
            "# Agent 评估报告",
            "",
            f"- 评估时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.get('timestamp', time.time())))}",
            f"- 样本数量: {report.get('sample_count', 0)}",
            f"- 评估耗时: {report.get('eval_latency_ms', 0):.0f}ms",
            "",
            "## 综合评分",
            "",
            f"**总体得分: {report.get('overall_score', 0) * 100:.1f} / 100**",
            "",
            "| 维度 | 得分 | 评级 |",
            "|------|------|------|",
        ]

        scores = report.get("dimension_scores", {})
        summary = report.get("summary", {})
        for dim in ["functional", "performance", "cost", "safety"]:
            score = scores.get(dim, 0)
            grade = summary.get(dim, "未知").split("（")[-1].rstrip("）") if dim in summary else "未知"
            lines.append(f"| {dim} | {score * 100:.1f} | {grade} |")

        lines.extend([
            "",
            "## 详细结果",
            "",
            "```json",
            json.dumps(report.get("details", {}), ensure_ascii=False, indent=2)[:2000],
            "```",
        ])

        return "\n".join(lines)

    @staticmethod
    def to_html(report: Dict[str, Any]) -> str:
        """将批量评估报告转为 HTML"""
        overall = report.get("overall_score", 0)
        scores = report.get("dimension_scores", {})
        color = "green" if overall >= 0.8 else "orange" if overall >= 0.6 else "red"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px;">
            <h2>Agent 评估报告</h2>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 8px;">
                <h3 style="color: {color};">综合得分: {overall * 100:.1f}</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #e0e0e0;">
                        <th style="padding: 8px; text-align: left;">维度</th>
                        <th style="padding: 8px; text-align: right;">得分</th>
                    </tr>
        """
        for dim, score in scores.items():
            html += f"""
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{dim}</td>
                        <td style="padding: 8px; text-align: right; border-bottom: 1px solid #ddd;">{score * 100:.1f}</td>
                    </tr>
            """
        html += """
                </table>
            </div>
        </div>
        """
        return html

    @staticmethod
    def to_streamlit_metrics(report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """转换为 Streamlit metrics 组件数据"""
        scores = report.get("dimension_scores", {})
        return [
            {"label": "综合得分", "value": f"{report.get('overall_score', 0) * 100:.1f}", "delta": None},
            {"label": "功能正确性", "value": f"{scores.get('functional', 0) * 100:.1f}", "delta": None},
            {"label": "性能效率", "value": f"{scores.get('performance', 0) * 100:.1f}", "delta": None},
            {"label": "成本控制", "value": f"{scores.get('cost', 0) * 100:.1f}", "delta": None},
            {"label": "安全合规", "value": f"{scores.get('safety', 0) * 100:.1f}", "delta": None},
        ]
