"""
模块名称: Evaluation Dashboard (评估仪表盘)
功能描述:
    为 Streamlit 提供评估数据可视化组件。
    展示实时评估指标、历史趋势、异常告警。
"""

from typing import Any, Dict, List, Optional

import streamlit as st
from src.evaluation.collector import TraceCollector
from src.evaluation.report import ReportFormatter


def render_evaluation_metrics(report: Dict[str, Any]):
    """渲染评估指标卡片"""
    if not report or "error" in report:
        st.warning("暂无评估数据")
        return

    scores = report.get("dimension_scores", {})
    overall = report.get("overall_score", 0)

    st.subheader("Agent 评估仪表盘")

    # 综合得分
    col1, col2, col3, col4, col5 = st.columns(5)
    metrics = [
        ("综合得分", overall, col1),
        ("功能正确性", scores.get("functional", 0), col2),
        ("性能效率", scores.get("performance", 0), col3),
        ("成本控制", scores.get("cost", 0), col4),
        ("安全合规", scores.get("safety", 0), col5),
    ]

    for label, score, col in metrics:
        with col:
            st.metric(
                label=label,
                value=f"{score * 100:.1f}",
                delta=f"{'优秀' if score >= 0.9 else '良好' if score >= 0.8 else '及格' if score >= 0.6 else '需改进'}",
            )

    # 评估摘要
    summary = report.get("summary", {})
    with st.expander("评估详情"):
        for key, text in summary.items():
            st.write(f"- {text}")

    # 成本详情（如有）
    cost_detail = report.get("details", {}).get("cost")
    if cost_detail and "savings_rate" in cost_detail:
        st.info(f"💰 成本节省率: {cost_detail['savings_rate'] * 100:.1f}%, "
                f"等效人力成本: ${cost_detail.get('human_cost_usd', 0):.2f}")

    # 性能详情（如有）
    perf_detail = report.get("details", {}).get("performance")
    if perf_detail and "end_to_end_latency" in perf_detail:
        latency = perf_detail["end_to_end_latency"]
        st.info(f"⚡ P95 延迟: {latency.get('p95_ms', 0):.0f}ms, "
                f"QPS: {perf_detail.get('throughput_qps', {}).get('qps', 0):.2f}")


def render_trace_history(n: int = 50):
    """渲染最近 Trace 历史"""
    collector = TraceCollector()
    traces = collector.get_recent_traces(n)

    if not traces:
        st.info("暂无 Trace 记录")
        return

    st.subheader(f"最近 {len(traces)} 条执行记录")

    data = []
    for t in traces:
        data.append({
            "trace_id": t.trace_id[:8],
            "agent": t.agent_name,
            "latency_ms": round(t.latency_ms, 0),
            "tokens": t.token_usage.get("total_tokens", 0),
            "model": t.model_name,
            "has_error": "是" if t.error else "否",
        })

    st.dataframe(data, use_container_width=True)


def render_evaluation_panel():
    """渲染完整的评估面板（供 Streamlit 侧边栏或独立页面使用）"""
    st.title("Agent 评估中心")

    collector = TraceCollector()
    traces = collector.get_recent_traces(100)

    if not traces:
        st.info("暂无评估数据。请先在主页面运行诊断流程，系统将自动采集 Trace 数据。")
        return

    # 实时评估
    if st.button("运行实时评估", type="primary"):
        with st.spinner("正在评估最近 100 条 Trace..."):
            from src.evaluation.orchestrator import EvaluationOrchestrator
            orchestrator = EvaluationOrchestrator(use_llm_judge=False)
            report = orchestrator.evaluate_recent_traces(min(100, len(traces)))

            if "error" not in report:
                st.session_state["last_eval_report"] = report
                st.success("评估完成！")
            else:
                st.error(f"评估失败: {report['error']}")

    # 显示上次评估结果
    if "last_eval_report" in st.session_state:
        render_evaluation_metrics(st.session_state["last_eval_report"])

        # 导出报告
        report = st.session_state["last_eval_report"]
        col1, col2 = st.columns(2)
        with col1:
            md_report = ReportFormatter.to_markdown(report)
            st.download_button(
                label="下载 Markdown 报告",
                data=md_report,
                file_name="evaluation_report.md",
                mime="text/markdown",
            )
        with col2:
            html_report = ReportFormatter.to_html(report)
            st.download_button(
                label="下载 HTML 报告",
                data=html_report,
                file_name="evaluation_report.html",
                mime="text/html",
            )

    # Trace 历史
    render_trace_history(30)
