"""
模块名称: Hierarchical Orchestrator (层级化诊断编排器)
功能描述:
    基于 Subagent + 层级化 MDT 的新版诊断编排器。
    与原版 orchestrator.py 的区别：
    - 原版：平级并发所有专科 Agent，固定流程。
    - 新版：MDT 父 Agent 动态规划并调度专科 Subagent，按需调用。

设计理念:
    1.  **按需会诊**: 根据病例特征选择性调用相关专科，减少无效计算。
    2.  **向后兼容**: 若层级化调度失败，自动降级为原版平级并发模式。
    3.  **统一出口**: 保持与原版相同的 generate_diagnosis 接口。
"""

import time
from typing import Dict, Optional

from src.agents.hierarchical_mdt import build_hierarchical_mdt
from src.agents.base import 多学科团队
from src.services.logging import log_info, log_warn
from src.services.cache import get_cache, DiagnosisCache
from src.services.graph_rag import retrieve_hybrid_knowledge_snippets
from src.core.settings import get_settings, Settings
from src.core.triage import triage_specialists


async def generate_hierarchical_diagnosis(medical_report: str, use_cache: bool = True):
    """
    层级化诊断生成器。
    接口与原版 generate_diagnosis 保持一致，内部使用 Subagent 架构。
    :param medical_report: 医疗报告文本
    :param use_cache: 是否启用缓存
    :yields: (阶段名称, 内容) 元组
    """
    settings: Settings = get_settings()
    start_time: float = time.time()

    # 缓存检查
    if use_cache and settings.enable_cache:
        cached = await _try_load_cache(medical_report, settings)
        if cached:
            yield "Status", "📋 从缓存加载诊断结果..."
            yield "Final Diagnosis", cached["diagnosis"]
            return

    yield "Status", "正在启动层级化诊断流程..."

    # RAG 预检索
    rag_context: Optional[str] = None
    try:
        rag_context = retrieve_hybrid_knowledge_snippets(medical_report)
    except Exception as e:
        log_warn(f"[HierarchicalOrchestrator] RAG 预检索失败: {e}")

    # 构建层级化 MDT
    try:
        mdt = build_hierarchical_mdt(medical_report, rag_context=rag_context)
        yield "Status", f"层级化 MDT 已初始化，注册专科: {len(mdt.subagents)} 个"

        # 执行层级化诊断
        yield "Status", "MDT 正在分析病例并规划专科调度..."
        final_diagnosis = await mdt.run_hierarchical_diagnosis()

        # 输出被调度的专科结果（用于前端展示）
        for specialist_name, report in (mdt.extra_info or {}).items():
            if report and not report.startswith("["):
                yield specialist_name, report

    except Exception as e:
        log_warn(f"[HierarchicalOrchestrator] 层级化诊断失败，降级为原版模式: {e}")
        yield "Status", "层级化调度异常，降级为标准多学科会诊..."
        # 降级：使用原版 MDT 逻辑
        from src.core.orchestrator import generate_diagnosis
        async for item in generate_diagnosis(medical_report, use_cache=False):
            yield item
        return

    yield "Final Diagnosis", final_diagnosis

    # 缓存保存
    if use_cache and settings.enable_cache and final_diagnosis:
        _save_to_cache(medical_report, final_diagnosis)

    total_time = time.time() - start_time
    log_info(f"[HierarchicalOrchestrator] 层级化诊断完成，总耗时: {total_time:.2f}秒")


async def _try_load_cache(medical_report: str, settings) -> dict | None:
    cache = get_cache()
    report_hash = DiagnosisCache.compute_hash(medical_report)
    return cache.get(report_hash, ttl=settings.cache_ttl)


def _save_to_cache(medical_report: str, diagnosis: str):
    try:
        cache = get_cache()
        report_hash = DiagnosisCache.compute_hash(medical_report)
        cache.set(report_hash, diagnosis, confidence=1.0)
    except Exception as e:
        log_warn(f"[HierarchicalOrchestrator] 保存缓存失败: {e}")
