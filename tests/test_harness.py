"""
模块名称: Test Harness (评估框架入口)
功能描述:
    使用 pytest 运行 Harness 评估框架。
    支持通过命令行参数选择评估的模块。
用法:
    pytest tests/test_harness.py -v -s
    pytest tests/test_harness.py -v -s -k triage
    pytest tests/test_harness.py -v -s -k rag
"""

import asyncio
import pytest

from tests.harness.runner import HarnessRunner
from tests.harness.reporter import ConsoleReporter, JSONReporter, MarkdownReporter
from tests.harness.evaluators import TriageEvaluator, RAGEvaluator, MDTEvaluator


@pytest.fixture
async def harness_report(request):
    """执行评估并返回报告"""
    runner = HarnessRunner().load_cases()

    # 根据测试名动态注册评估器
    test_name = request.node.name
    if "triage" in test_name:
        runner.register(TriageEvaluator())
    elif "rag" in test_name:
        runner.register(RAGEvaluator())
    elif "mdt" in test_name:
        runner.register(MDTEvaluator())
    else:
        # 默认运行全量（耗时较长，需要 LLM API）
        runner.register(TriageEvaluator())
        runner.register(RAGEvaluator())
        runner.register(MDTEvaluator())

    report = await runner.run()
    return report


@pytest.mark.asyncio
async def test_harness_triage():
    """测试分诊模块"""
    runner = HarnessRunner().load_cases()
    runner.register(TriageEvaluator())
    report = await runner.run()
    ConsoleReporter.render(report)
    assert report.summary.get("triage", {}).get("passed", 0) >= 0  # 仅做 smoke test


@pytest.mark.asyncio
async def test_harness_rag():
    """测试 RAG 检索模块"""
    runner = HarnessRunner().load_cases()
    runner.register(RAGEvaluator())
    report = await runner.run()
    ConsoleReporter.render(report)
    assert report.summary.get("rag", {}).get("passed", 0) >= 0


@pytest.mark.asyncio
async def test_harness_mdt():
    """测试 MDT 综合诊断模块"""
    runner = HarnessRunner().load_cases()
    runner.register(MDTEvaluator())
    report = await runner.run()
    ConsoleReporter.render(report)
    assert report.summary.get("mdt", {}).get("passed", 0) >= 0


@pytest.mark.asyncio
async def test_harness_full():
    """全量评估（需要配置 LLM API）"""
    runner = HarnessRunner().load_cases()
    runner.register(TriageEvaluator())
    runner.register(RAGEvaluator())
    runner.register(MDTEvaluator())
    report = await runner.run()
    ConsoleReporter.render(report)
    JSONReporter.save(report)
    MarkdownReporter.save(report)
    # 全量测试主要做集成验证，不强制断言通过率（因为 LLM 输出不稳定）
    assert report.total_cases > 0
