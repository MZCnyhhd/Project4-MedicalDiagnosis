# 🏥 健康医疗 AI 智能平台（MN Health-Medical AI Platform）

> 由 **Project3-HealthInsights（体检报告智能洞察）** 与 **Project4-MedicalDiagnostics（医疗诊断 AI 智能体）** 融合而成的一站式健康医疗 AI 平台。
>
> 以 Project4 的企业级多智能体架构为主干，并入 Project3 的体检报告结构化分析能力，覆盖 **从个人健康管理到临床疾病诊断** 的完整场景。

在线展示页（GitHub Pages）：<https://mzcnyhhd.github.io/Project2-Medical/>

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
```bash
pip install -r requirements.txt
```

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

## 🔒 安全与合规
- 所有密钥（`config/apikey.env`）、本地数据库（`*.db`）、认证凭据（`config/auth.yaml`）均不纳入版本控制。
- 本平台输出由 AI 生成，**仅供研究与参考，不构成专业医疗建议**。实际诊疗请咨询执业医师。

## 📄 License
见 [LICENSE](./LICENSE)。
