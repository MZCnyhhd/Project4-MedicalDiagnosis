"""
模块名称: Health Report Analysis Orchestrator (体检报告分析编排器)

功能描述:

    融合自 Project3-HealthInsights 的“体检报告智能分析”能力。
    面向个人健康管理场景：上传体检报告 -> RAG 知识增强 -> 结构化体检解读。
    与 MDT 疾病诊断（orchestrator.py）并列，作为平台的第二大业务模式。

设计理念:

    1.  **能力复用**: 复用平台统一的 LLM 工厂（支持 Qwen/Groq/OpenAI/Gemini/Ollama 多供应商）。
    2.  **知识增强**: 复用平台的 RAG / 知识图谱检索能力，增强体检解读的权威性。
    3.  **流式反馈**: 采用生成器（Generator）模式，与 MDT 诊断流程保持一致的 UI 体验。

线程安全性:

    - 在 Streamlit 脚本线程中通过 asyncio.run 驱动，无跨请求共享状态。

依赖关系:

    - `src.services.llm`: 统一模型工厂。
    - `src.services.graph_rag`: 检索增强。
    - `src.agents.base`: PROMPTS_CONFIG 提示词配置。
"""

# [导入模块] ############################################################################################################
import time                                                            # 时间工具：性能计时
from langchain_core.prompts import PromptTemplate                      # LangChain 提示词模板
# [内部模块 | Internal Modules] =========================================================================================
from src.services.llm import get_chat_model                            # 统一模型工厂
from src.services.graph_rag import retrieve_hybrid_knowledge_snippets  # 检索增强
from src.services.logging import log_info, log_warn                    # 统一日志服务
from src.agents.base import PROMPTS_CONFIG                             # 提示词配置

# [创建全局变量] =========================================================================================================
# 兜底提示词：当 config/prompts.yaml 未配置 health_checkup_analyst 时使用
_DEFAULT_HEALTH_PROMPT: str = (
    "你是一位专业的体检报告分析师，拥有检验医学与内科的全面知识。\n"
    "请基于以下体检报告，输出结构化解读：\n"
    "1. 异常指标总结（按系统/器官分组）；\n"
    "2. 健康建议（饮食、运动、睡眠、预防、复查）；\n"
    "3. 免责声明。\n"
    "请使用 Markdown 格式输出。\n\n"
    "体检报告：{medical_report}"
)


# [定义函数] ############################################################################################################
# [异步-外部-生成体检报告分析] ============================================================================================
async def generate_health_report(medical_report: str, use_rag: bool = True):
    """
    体检报告分析的异步生成器。
    流程：RAG 知识增强 -> 结构化体检解读（单 Agent）。
    :param medical_report: 体检报告文本
    :param use_rag: 是否启用检索增强
    :yields: (阶段名称, 内容) 元组，阶段为 "Status" 或 "Final Report"
    """
    # [step1] 初始化计时
    start_time: float = time.time()

    # [step2] RAG 知识增强（可选）
    rag_context = None
    if use_rag:
        yield "Status", "正在检索健康管理相关知识..."
        try:
            rag_context = retrieve_hybrid_knowledge_snippets(medical_report)
        except Exception as e:
            log_warn(f"[HealthAnalysis] RAG 检索失败，将不使用知识增强: {e}")

    # [step3] 构建结构化体检分析提示词
    yield "Status", "🩺 体检分析师正在解读报告..."
    template_str: str = PROMPTS_CONFIG.get("health_checkup_analyst") or _DEFAULT_HEALTH_PROMPT
    prompt: str = PromptTemplate.from_template(template_str).format(medical_report=medical_report)
    if rag_context:
        prompt = (
            "### 参考医学知识 (RAG)\n"
            "以下是从权威医学库检索到的相关信息，请结合参考：\n"
            f"{rag_context}\n\n---\n\n"
            f"{prompt}"
        )

    # [step4] 调用统一 LLM 工厂生成分析结果
    try:
        model = get_chat_model()
        response = await model.ainvoke(prompt)
        result: str = getattr(response, "content", str(response))
    except Exception as e:
        log_warn(f"[HealthAnalysis] 模型调用失败: {e}")
        result = f"体检报告分析暂时不可用，请稍后重试。错误信息：{e}"

    # [step5] 记录耗时并产出最终报告
    log_info(f"[HealthAnalysis] 体检报告分析完成，耗时: {time.time() - start_time:.2f}秒")
    yield "Final Report", result
