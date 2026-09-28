"""
模块名称: Sidebar Component (侧边栏组件)
功能描述:

    渲染应用的左侧控制面板。
    包含模型选择、知识库管理 (上传/重建)、缓存清理等系统级操作入口。

设计理念:

    1.  **功能聚合**: 将配置和管理类功能集中在侧边栏，保持主界面 (Main Content) 专注于诊断业务。
    2.  **即时反馈**: 操作 (如切换模型) 立即生效，通常通过修改环境变量或 Session State 实现。
    3.  **状态可视**: 显示当前连接的模型、数据库状态等信息。

线程安全性:

    - 依赖 Streamlit 的渲染线程，操作 Session State 需注意并发 (但在 Streamlit 中通常是单线程模型)。

依赖关系:

    - `streamlit`: UI 框架。
    - `src.core.settings`: 读取和修改配置。
"""

import os
import streamlit as st

# [配置常量] ############################################################################################################
# 各云端模型后端对应的密钥 / 模型配置。
# 背景：云端部署（如 Streamlit Community Cloud）没有 config/apikey.env 文件，
#      用户无法编辑配置文件，必须能在界面上直接填入自己的 API Key。
# 说明：key_env 为密钥环境变量名；model_env / base_env 为可选的模型名与网关地址覆盖项。
PROVIDER_CONFIG: dict[str, dict[str, str]] = {
    "mimo": {
        "key_env": "MIMO_API_KEY",
        "key_label": "MiMo API Key（小米）",
        "key_hint": "前往小米 MiMo 开放平台控制台获取 API Key",
        "model_env": "MIMO_MODEL",
        "model_label": "对话模型名称",
        "model_default": "mimo-v2.5-pro",
        "base_env": "MIMO_BASE_URL",
        "base_label": "API Base URL",
        "base_default": "https://api.xiaomimimo.com/v1",
    },
    "qwen": {
        "key_env": "DASHSCOPE_API_KEY",
        "key_label": "DashScope API Key（通义千问）",
        "key_hint": "前往阿里云百炼（DashScope）控制台获取 API Key",
        "model_env": "QWEN_MODEL",
        "model_label": "对话模型名称",
        "model_default": "qwen-max",
        "base_env": "",
        "base_label": "",
        "base_default": "",
    },
    "baichuan": {
        "key_env": "BAICHUAN_API_KEY",
        "key_label": "Baichuan API Key（百川）",
        "key_hint": "前往百川智能开放平台控制台获取 API Key",
        "model_env": "BAICHUAN_MODEL",
        "model_label": "对话模型名称",
        "model_default": "Baichuan-M2",
        "base_env": "",
        "base_label": "",
        "base_default": "",
    },
    "groq": {
        "key_env": "GROQ_API_KEY",
        "key_label": "Groq API Key",
        "key_hint": "前往 https://console.groq.com/keys 创建 API Key",
        "model_env": "GROQ_MODEL",
        "model_label": "对话模型名称",
        "model_default": "llama-3.3-70b-versatile",
        "base_env": "",
        "base_label": "",
        "base_default": "",
    },
}

# [定义函数] ############################################################################################################
# [内部-渲染API Key配置] ==================================================================================================
def _render_api_key_config(provider: str) -> None:
    """
    渲染当前所选模型后端对应的 API Key 输入区（运行时即时生效）。

    安全设计：
        输入框 **不回填** 已有密钥，只显示「已配置 / 未配置」状态。
        原因：公开部署时 Streamlit 的控件值会下发到浏览器端，
        若回填真实 Key 会造成密钥泄露；此处仅允许「覆盖写入」。

    :param provider: 模型后端标识（mimo / qwen / baichuan / groq）
    """
    from src.core.settings import set_runtime_config

    meta = PROVIDER_CONFIG.get(provider)
    if not meta:
        return None

    st.markdown("**🔑 API Key 配置**")
    key_env = meta["key_env"]

    # [step1] 密钥输入框（不回填既有值，避免公开部署时泄露到浏览器）
    typed = st.text_input(
        meta["key_label"],
        value="",
        type="password",
        placeholder="已配置，如需更换请重新粘贴" if os.getenv(key_env) else "请粘贴你的 API Key",
        help=f"{meta['key_hint']}。留空则沿用配置文件 / Secrets 中已有的密钥。",
        key=f"apikey_input_{key_env}",
    )
    if typed.strip():
        if set_runtime_config(key_env, typed):
            st.toast(f"已更新 {meta['key_label']}", icon="🔑")

    # [step2] 配置状态提示
    if os.getenv(key_env):
        st.caption("✅ 密钥已就绪，可直接使用该模型")
    else:
        st.caption(f"⚠️ 未配置密钥，使用该模型会失败；请粘贴 Key 或改用其他后端")

    # [step3] 高级设置：模型名 / 网关地址（非密钥，可安全回填）
    with st.expander("⚙️ 高级设置（模型名 / 网关地址）", expanded=False):
        model_env = meta.get("model_env", "")
        if model_env:
            model_val = st.text_input(
                meta["model_label"],
                value=os.getenv(model_env, meta.get("model_default", "")),
                help="留空使用默认值；不同账号可用的模型名可能不同",
                key=f"model_input_{model_env}",
            )
            if model_val.strip():
                set_runtime_config(model_env, model_val)

        base_env = meta.get("base_env", "")
        if base_env:
            base_val = st.text_input(
                meta["base_label"],
                value=os.getenv(base_env, meta.get("base_default", "")),
                help="如需走自建网关 / 代理，可在此覆盖接口地址",
                key=f"base_input_{base_env}",
            )
            if base_val.strip():
                set_runtime_config(base_env, base_val)

    return None

# [UI-渲染侧边栏] =========================================================================================================
def render_sidebar():
    """渲染侧边栏组件"""
    with st.sidebar:
        st.subheader("🤖 选择大模型")
        
        # [step1] 模型切换功能
        model_options = {
            "MiMo V2.5 Pro (小米)": "mimo",
            "Qwen-Turbo (通义千问)": "qwen",
            "Baichuan M2 (百川)": "baichuan",
            "Groq (Llama-3.3-70B)": "groq",
            "Ollama Service (本地服务)": "ollama",
            "HuggingFace Native (原生加载)": "local"
        }
        
        # 清理选项重命名后残留的旧 session_state 值，避免 selectbox 渲染异常/空白
        if st.session_state.get("model_selector") not in model_options:
            st.session_state.pop("model_selector", None)
        
        # 获取当前环境变量中的默认值
        current_provider = os.getenv("LLM_PROVIDER", "qwen")
        # 反向查找对应的 index
        default_index = 0
        for idx, (name, key) in enumerate(model_options.items()):
            if key == current_provider:
                default_index = idx
                break
        
        # 使用 radio 替代 selectbox：确保所选模型始终可见（selectbox 在部分环境下选中值渲染为空白）
        selected_model_name = st.radio(
            "模型后端",
            options=list(model_options.keys()),
            index=default_index,
            key="model_selector",
            help="选择用于诊断的底层大语言模型",
        )
        
        # 更新环境变量
        selected_key = model_options[selected_model_name]
        os.environ["LLM_PROVIDER"] = selected_key
        # 显示当前生效模型，便于确认切换结果（醒目提示，避免选择框空白时无法确认）
        st.success(f"✅ 当前生效模型：{selected_model_name}")

        # [step2] API Key 配置：按所选后端动态显示对应密钥输入框
        # 目的：云端/演示环境无法编辑 config/apikey.env，用户需在界面直接填入 Key 并即时生效
        if selected_key in PROVIDER_CONFIG:
            _render_api_key_config(selected_key)

        # [step2-1] Ollama 模型配置
        if selected_key == "ollama":
            ollama_base = st.text_input(
                "Ollama 地址",
                value=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                help="Ollama 服务的 API 地址"
            )
            os.environ["OLLAMA_BASE_URL"] = ollama_base
            
            ollama_model = st.text_input(
                "Ollama 模型名称",
                value=os.getenv("OLLAMA_MODEL", "FreedomIntelligence/HuatuGPT-7B"),
                placeholder="例如: llama3, gemma:latest",
                help="请输入已在 Ollama 中下载的模型名称"
            )
            os.environ["OLLAMA_MODEL"] = ollama_model
            
            # 显示状态检查
            if st.button("测试 Ollama 连接", use_container_width=True):
                try:
                    import requests
                    # 临时清除代理环境变量以避免 localhost 连接问题
                    proxies = {"http": None, "https": None}
                    resp = requests.get(ollama_base, timeout=2, proxies=proxies)
                    if resp.status_code == 200:
                        st.success("✅ 服务连接成功")
                        # 检查模型
                        try:
                            tags = requests.get(f"{ollama_base}/api/tags", timeout=2, proxies=proxies).json()
                            models = [m['name'] for m in tags.get('models', [])]
                            # 不区分大小写匹配
                            target = ollama_model.lower()
                            # 处理 :latest 后缀
                            if ":" not in target:
                                target += ":latest"
                            
                            found = False
                            for m in models:
                                m_lower = m.lower()
                                if target == m_lower:
                                    found = True
                                    break
                                # 尝试如果不带 latest
                                if target.replace(":latest", "") == m_lower:
                                    found = True
                                    break
                                    
                            if found:
                                st.success(f"✅ 模型 {ollama_model} 已就绪")
                            else:
                                st.warning(f"⚠️ 未找到模型 {ollama_model}，请先执行 pull")
                                st.info(f"可用模型: {', '.join(models)}")
                        except:
                            pass
                    else:
                        st.error(f"❌ 服务异常: {resp.status_code}")
                except Exception as e:
                    st.error(f"❌ 无法连接到 Ollama: {str(e)}")

        # [step2-2] HuggingFace 本地模型路径配置
        if selected_key == "local":
            local_path = st.text_input(
                "大语言模型路径 (LLM)",
                value=os.getenv("LOCAL_MODEL_PATH", ""),
                placeholder="例如: models/qwen-7b-chat",
                help="请输入本地 HuggingFace 模型目录的绝对路径"
            )
            if local_path:
                os.environ["LOCAL_MODEL_PATH"] = local_path
            else:
                st.warning("请设置本地模型路径")

            local_embedding = st.text_input(
                "Embedding 模型路径",
                value=os.getenv("LOCAL_EMBEDDING_MODEL", ""),
                placeholder="例如: models/bge-small-zh",
                help="请输入本地 Embedding 模型目录的绝对路径"
            )
            if local_embedding:
                os.environ["LOCAL_EMBEDDING_MODEL"] = local_embedding
        
        st.subheader("📚 知识库管理")
        
        # [step3] 知识库管理按钮
        # 分两个按钮，明确功能区分
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 更新向量库", use_container_width=True, 
                        help="更新 RAG 检索用的向量索引 (Pinecone/FAISS)"):
                with st.spinner("正在处理文档..."):
                    from src.scripts.ingest_knowledge import ingest_docs
                    status = ingest_docs()
                    if "成功" in status:
                        st.toast(status, icon="✅")
                    else:
                        st.error(status)
        
        with col2:
            # Neo4j 按钮（如果启用）
            from src.core.settings import get_settings
            settings = get_settings()
            
            if settings.enable_neo4j:
                if st.button("🕸️ 更新图谱", use_container_width=True, 
                            help="更新 Neo4j 知识图谱（需要较长时间）"):
                    with st.spinner("正在构建知识图谱..."):
                        try:
                            from src.scripts.build_kg import build_knowledge_graph
                            result = build_knowledge_graph()
                            if result and "成功" in result:
                                st.toast(result, icon="✅")
                            else:
                                st.toast("知识图谱构建完成", icon="✅")
                        except Exception as e:
                            st.error(f"构建失败: {str(e)}")
            else:
                st.button("🕸️ 图谱未启用", use_container_width=True, disabled=True,
                         help="在配置中设置 ENABLE_NEO4J=true 以启用")
        
        # [step4] 缓存清理
        if st.button("🗑️ 清除缓存", use_container_width=True,
                    help="清除诊断结果缓存，释放存储空间"):
            from src.services.cache import get_cache
            cache = get_cache()
            deleted_count = cache.clear_all()
            if deleted_count > 0:
                st.toast(f"已清除 {deleted_count} 条缓存记录", icon="🗑️")
            else:
                st.toast("缓存已清空", icon="✅")
        
