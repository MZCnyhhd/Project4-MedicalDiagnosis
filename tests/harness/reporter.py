"""
模块名称: Harness Reporter (评估报告器)
功能描述:
    将 HarnessReport 输出为多种格式：控制台表格、JSON 文件、Markdown 报告。
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

from tests.harness.base import HarnessReport, EvalResult


class ConsoleReporter:
    """控制台表格报告"""

    @staticmethod
    def render(report: HarnessReport):
        print("\n" + "=" * 80)
        print("医疗诊断 AI 智能体 — 评估报告".center(80))
        print("=" * 80)
        print(f"总用例数: {report.total_cases}")
        print(f"总评估次数: {report.summary.get('total_evaluations', 0)}")
        print(f"通过: {report.summary.get('passed', 0)} | 失败: {report.summary.get('failed', 0)} | 错误: {report.summary.get('errors', 0)}")
        print(f"平均延迟: {report.summary.get('avg_latency_ms', 0)} ms")
        print("-" * 80)

        # 按评估器输出指标均值
        for key, value in report.summary.items():
            if isinstance(value, dict) and "metric_avgs" in value:
                print(f"\n[{key}] 评估次数: {value['count']} | 通过: {value['passed']} | 平均延迟: {value['avg_latency_ms']} ms")
                for metric_name, avg_score in value["metric_avgs"].items():
                    status = "✅" if avg_score >= 0.5 else "⚠️"
                    print(f"  {status} {metric_name}: {avg_score:.4f}")

        print("\n" + "-" * 80)
        print("详细结果:")
        for r in report.results:
            status = "✅ PASS" if r.passed else ("❌ FAIL" if not r.error else "💥 ERROR")
            print(f"  [{status}] {r.evaluator_name} / {r.test_case_id} ({r.latency_ms:.0f}ms)")
            for m in r.metrics:
                print(f"      - {m.metric_name}: {m.score:.4f}")
            if r.error:
                print(f"      - error: {r.error}")
        print("=" * 80 + "\n")


class JSONReporter:
    """JSON 文件报告"""

    @staticmethod
    def save(report: HarnessReport, output_path: str = None):
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"tests/harness/reports/harness_report_{timestamp}.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report.to_json(indent=2))
        print(f"[JSONReporter] 报告已保存至: {output_path}")


class MarkdownReporter:
    """Markdown 报告（适合放入文档或 CI 展示）"""

    @staticmethod
    def save(report: HarnessReport, output_path: str = None):
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"tests/harness/reports/harness_report_{timestamp}.md"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        lines = [
            "# 医疗诊断 AI 智能体评估报告",
            f"",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**总用例数**: {report.total_cases}",
            f"**总评估次数**: {report.summary.get('total_evaluations', 0)}",
            f"",
            "## 汇总统计",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 通过 | {report.summary.get('passed', 0)} |",
            f"| 失败 | {report.summary.get('failed', 0)} |",
            f"| 错误 | {report.summary.get('errors', 0)} |",
            f"| 平均延迟(ms) | {report.summary.get('avg_latency_ms', 0)} |",
            "",
            "## 按评估器统计",
            "",
        ]
        for key, value in report.summary.items():
            if isinstance(value, dict) and "metric_avgs" in value:
                lines.append(f"### {key}")
                lines.append(f"- 评估次数: {value['count']}")
                lines.append(f"- 通过次数: {value['passed']}")
                lines.append(f"- 平均延迟: {value['avg_latency_ms']} ms")
                lines.append("")
                lines.append("| 指标 | 平均分 |")
                lines.append("|------|--------|")
                for metric_name, avg_score in value["metric_avgs"].items():
                    lines.append(f"| {metric_name} | {avg_score:.4f} |")
                lines.append("")

        lines.append("## 详细结果")
        lines.append("")
        lines.append("| 评估器 | 用例 | 状态 | 延迟(ms) |")
        lines.append("|--------|------|------|----------|")
        for r in report.results:
            status = "PASS" if r.passed else ("FAIL" if not r.error else "ERROR")
            lines.append(f"| {r.evaluator_name} | {r.test_case_id} | {status} | {r.latency_ms:.0f} |")
        lines.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"[MarkdownReporter] 报告已保存至: {output_path}")
