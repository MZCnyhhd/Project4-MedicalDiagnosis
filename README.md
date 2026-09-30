# 🏥 健康医疗 AI 智能平台（MN Health-Medical AI Platform）

> 由 **Project3-HealthInsights（体检报告智能洞察）** 与 **Project4-MedicalDiagnostics（医疗诊断 AI 智能体）** 融合而成的一站式健康医疗 AI 平台。
>
> 以 Project4 的企业级多智能体架构为主干，并入 Project3 的体检报告结构化分析能力，覆盖 **从个人健康管理到临床疾病诊断** 的完整场景。

在线展示页（GitHub Pages）：<https://mzcnyhhd.github.io/Project4-MedicalDiagnosis/>

医学知识库在线浏览站：<https://mzcnyhhd.github.io/Project4-MedicalDiagnosis/kb/>

---

## ✨ 平台双模式

平台在登录后提供两种业务模式，可在主界面顶部一键切换：

| 模式 | 说明 | 来源 |
| :--- | :--- | :--- |
| 🩺 **疾病诊断会诊 (MDT)** | 智能分诊 → 多专科 AI 医生并发会诊 → 多学科团队 ReAct 综合诊断，RAG + 知识图谱增强 | Project4 |
| 📋 **体检报告分析** | 上传体检报告 → 结构化指标解读 + 异常总结 + 健康建议，RAG 知识增强 | Project3 |

两种模式均支持 **Markdown / PDF 双格式导出**，并共享统一的多模型 LLM 工厂与会话历史。

---

## 🧩 融合架构说明

### 主干：Project4（企业级医疗诊断引擎）
- **多智能体 MDT**：`src/agents/`（Agent 基类、多学科团队、ReAct 推理）
- **诊断编排**：`src/core/orchestrator.py`（缓存 → 分诊 → 并发专科 → 综合）
- **知识增强**：`src/services/rag.py` / `graph_rag.py` / `kg.py`（RAG + Neo4j 知识图谱）
- **统一 LLM 工厂**：`src/services/llm.py`（多供应商 + Fallback 容灾）
- **本地认证与权限**：`src/services/auth.py`（streamlit-authenticator，RBAC：admin/doctor/nurse）
- **本地存储**：`src/services/db.py`（SQLite 会诊记录）
- **扩展能力**：Skills 技能系统、MCP 协议、Evaluation 评估框架

### 并入：Project3（体检报告智能分析）
- **体检分析编排器**：`src/core/health_analysis.py`（新增，流式生成器，复用统一 LLM 工厂与 RAG）
- **结构化体检提示词**：`config/prompts.yaml` → `health_checkup_analyst`
- **Groq 模型支持**：`src/services/llm.py` → `_init_groq`（OpenAI 兼容接口，无需额外依赖）
- **PDF 导出**：`src/tools/export.py` → `create_analysis_pdf`（reportlab，内置中文 CID 字体）
- **PDF 表格提取增强**：`src/utils/file_processors.py`（优先 pdfplumber，回退 pypdf）
- **体检示例报告**：`data/medical_reports/Examples/example_04_health_checkup.txt`

### 融合决策
- **认证与存储**：统一采用本地方案（streamlit-authenticator + SQLite），**移除 Supabase 依赖**，离线可跑、隐私友好。
- **LLM 层**：统一到 LangChain 工厂，新增 Groq provider，支持 Qwen / Baichuan / Groq / OpenAI / Gemini / Ollama / 本地 HuggingFace 多供应商自动容灾。

---

## 🚀 快速开始

### 1. 安装依赖

**本地全功能**（含影像分析、本地模型）：
```bash
pip install -r requirements-full.txt
```

**云端 / 轻量环境**：
```bash
pip install -r requirements.txt
```

> `requirements.txt` 是云端精简版：`torch` / `torchvision` / `torchxrayvision` /
> `transformers` / `faiss` 等重依赖全部省略（它们在代码中均为**延迟导入**），
> 可省下 700MB+ 内存占用。代价是「🔬 影像医疗诊断」「本地 HuggingFace 模型」
> 「本地 FAISS 向量库」不可用 —— 应用会自动探测并禁用影像模式并给出提示。

### 2. 配置 API Key
```bash
cp config/apikey.env.example config/apikey.env
```
编辑 `config/apikey.env`，至少配置一个 LLM 提供商的 Key（如 `DASHSCOPE_API_KEY` 或 `GROQ_API_KEY`）。
> `config/apikey.env` 与 `config/auth.yaml` 均已被 `.gitignore` 忽略，不会提交到仓库。

### 3. 启动应用
```bash
streamlit run app.py
```
首次启动会自动生成 `config/auth.yaml`，默认账号：

| 角色 | 用户名 | 密码 |
| :--- | :--- | :--- |
| 管理员 | `admin` | `admin123` |
| 医生 | `doctor` | `doctor123` |
| 护士 | `nurse` | `nurse123` |

> ⚠️ 请在生产环境部署前修改默认密码。

---

## ☁️ 部署到 Streamlit Community Cloud

本项目已适配 Streamlit Cloud 免费层（1GB 内存），无需改动配置代码即可上线。

### 1. 创建应用
1. 打开 <https://share.streamlit.io>，用 GitHub 账号登录并授权；
2. 点击 **Create app** → **Deploy a public app from GitHub**，填写：

| 字段 | 值 |
| :--- | :--- |
| Repository | `MZCnyhhd/Project4-MedicalDiagnosis` |
| Branch | `main` |
| Main file path | `app.py` |

### 2. 配置密钥（必做）
展开 **Advanced settings** → **Secrets**，把 `.streamlit/secrets.toml` 的内容**整份粘贴**进去。

该文件由 `config/apikey.env` 生成，已被 `.gitignore` 忽略。平台上的 `st.secrets`
会在应用启动时被 `app.py` 自动注入环境变量，供 `src/core/settings.py` 读取，
因此**无需修改任何配置代码**。

### 3. 登录密码持久化（强烈建议）
云端容器的文件系统是临时的：容器重启后 `config/auth.yaml` 会被重置，
**你改过的密码会丢失并回退到默认账号**（`admin` / `admin123`）。

如需持久化，把完整认证 YAML 作为 `AUTH_CONFIG_YAML` 一并写入 Secrets：

```toml
AUTH_CONFIG_YAML = """
cookie:
  expiry_days: 30
  key: 换成一个随机字符串
  name: medical_auth_cookie
credentials:
  usernames:
    admin:
      email: you@example.com
      failed_login_attempts: 0
      logged_in: false
      name: 系统管理员
      password: $2b$12$把下面的哈希粘贴到这里
      role: admin
"""
```

生成新密码的 bcrypt 哈希：
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'你的新密码', bcrypt.gensalt()).decode())"
```

### 4. 云端能力差异

| 能力 | 云端 | 说明 |
| :--- | :--- | :--- |
| 🩺 疾病诊断会诊 (MDT) | ✅ | 走 DashScope / Pinecone 云端服务 |
| 📋 体检报告分析 | ✅ | 走统一 LLM 工厂 |
| 🔬 影像医疗诊断（胸部X光） | ❌ | 依赖 torch/torchxrayvision，精简版未安装，UI 会自动禁用并提示 |
| 本地 HuggingFace 模型 | ❌ | 需 GPU 与大内存，建议本地运行 |
| 本地 FAISS 向量库 | ❌ | 云端改用 Pinecone 云端索引 |

---

## 📁 目录结构
```
MN-HealthMedicalPlatform/
├── app.py                         # Streamlit 应用入口（双模式切换）
├── config/                        # 配置（API Key 模板、提示词、认证）
├── data/                          # 医学知识库、示例报告、字体
├── src/
│   ├── agents/                    # 多智能体与 MDT 团队
│   ├── core/                      # 编排器（诊断 + 体检分析）、配置、分诊
│   ├── services/                  # LLM 工厂、RAG、KG、认证、DB、缓存、日志
│   ├── skills/  mcp/  evaluation/ # 技能系统、MCP 协议、评估框架
│   ├── tools/   ui/    utils/     # 导出、界面、文件处理
├── docs/                          # GitHub Pages 展示页
└── tests/                         # 测试与评估 harness
```

---

## 💳 收费功能（微信收款）

平台支持**付费解锁**：非免费角色点击「开始诊断 / 开始分析 / 开始影像分析」时，
先展示微信收款码，扫码支付并确认后解锁，**当前会话内不限次数**。

| 项 | 说明 |
| :--- | :--- |
| 收款方式 | 个人微信收款码（`assets/wechat_pay_qr.png`） |
| 默认金额 | **¥9.9**（`PAYWALL_PRICE` 可改） |
| 免费角色 | `admin` 直通（`PAYWALL_FREE_ROLES` 可改，逗号分隔） |
| 总开关 | `PAYWALL_ENABLED=false` 可整体关闭收费拦截 |
| 解锁粒度 | 会话级（`st.session_state.paywall_paid`），刷新/重新登录后需重新支付 |

### 运行机制与局限（重要）

个人收款码**没有支付回调**，平台无法自动核销，因此采用「扫码支付 → 勾选确认 → 解锁」的
**软校验**模式：它拦截的是流程与心理成本，不构成强校验。

> 若需要**自动核销**（支付成功即解锁、可查订单、可退款），必须换成商户号方案：
> 微信支付 Native 支付（扫码）+ 服务端异步回调验签，需要企业主体与商户号。

### 配置方式

在环境变量或 `.streamlit/secrets.toml` / Streamlit Cloud Secrets 中按需配置：

```toml
PAYWALL_ENABLED = true
PAYWALL_PRICE = "9.9"
PAYWALL_FREE_ROLES = "admin"
```

更换收款码：直接用新图片覆盖 `assets/wechat_pay_qr.png`（保持文件名不变）即可。

---

## 🔒 安全与合规
- 所有密钥（`config/apikey.env`）、本地数据库（`*.db`）、认证凭据（`config/auth.yaml`）均不纳入版本控制。
- 本平台输出由 AI 生成，**仅供研究与参考，不构成专业医疗建议**。实际诊疗请咨询执业医师。

## 📄 License
见 [LICENSE](./LICENSE)。
