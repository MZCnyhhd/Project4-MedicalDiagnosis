"""
模块名称: MCP Adapter (Model Context Protocol 适配层)
功能描述:
    为医疗诊断系统提供轻量级 MCP 协议适配，将 RAG、知识图谱、诊断工具等
    封装为标准化的 MCP Server，使 Agent 可通过统一协议访问外部资源。

设计理念:
    1.  协议解耦：Agent 不直接依赖具体服务实现，只依赖 MCP 接口。
    2.  即插即用：新增数据源只需实现 MCPAdapter，无需修改 Agent 代码。
    3.  向后兼容：保留原有直接调用方式，MCP 作为可选增强层。

MCP 核心概念（简化版）:
    - Server: 提供资源和工具的服务端。
    - Client: 消费资源和工具的客户端（Agent 侧）。
    - Resource: 可读的数据源（如检索结果、图谱子图）。
    - Tool:   可调用的功能（如结构化诊断生成）。
"""
