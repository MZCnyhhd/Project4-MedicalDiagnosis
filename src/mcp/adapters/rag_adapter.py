"""
模块名称: RAG MCP Adapter (RAG MCP 适配器)
功能描述:
    将 RAG/GraphRAG 检索服务封装为 MCP Server。
    提供向量检索资源和混合检索工具。
"""

from typing import List

from src.mcp.server import MCPServer
from src.mcp.protocol import (
    MCPResource,
    MCPTool,
    MCPReadResourceRequest,
    MCPReadResourceResult,
    MCPCallToolRequest,
    MCPCallToolResult,
)
from src.services.graph_rag import retrieve_hybrid_knowledge_snippets, extract_medical_entities


class RAGMCPServer(MCPServer):
    """RAG 检索 MCP Server"""

    def __init__(self):
        super().__init__("medical-rag-server")

    def list_resources(self) -> List[MCPResource]:
        return [
            MCPResource(
                uri="rag://knowledge_base",
                name="医学知识库",
                description="基于向量数据库和知识图谱的混合医学知识库",
            ),
        ]

    def list_tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name="hybrid_retrieve",
                description="根据患者报告执行混合检索（向量 + 知识图谱），返回相关医学知识",
                input_schema={"report": {"type": "string", "description": "患者医疗报告"}},
            ),
            MCPTool(
                name="extract_entities",
                description="从患者报告中提取医学实体",
                input_schema={"report": {"type": "string"}},
            ),
        ]

    def read_resource(self, request: MCPReadResourceRequest) -> MCPReadResourceResult:
        if request.uri == "rag://knowledge_base":
            return MCPReadResourceResult(
                contents="医学知识库包含 150+ 种疾病的权威诊疗信息，支持向量语义检索和知识图谱关联查询。",
                metadata={"disease_count": 150, "sources": ["knowledge_base", "vector_store", "graph_db"]},
            )
        return MCPReadResourceResult(contents="", is_error=True)

    def call_tool(self, request: MCPCallToolRequest) -> MCPCallToolResult:
        if request.name == "hybrid_retrieve":
            report = request.arguments.get("report", "")
            try:
                context = retrieve_hybrid_knowledge_snippets(report)
                return MCPCallToolResult(content=context or "未检索到相关知识")
            except Exception as e:
                return MCPCallToolResult(content=f"检索失败: {e}", is_error=True)
        elif request.name == "extract_entities":
            report = request.arguments.get("report", "")
            try:
                entities = extract_medical_entities(report)
                entity_names = [e.name for e in entities]
                return MCPCallToolResult(content=f"提取实体: {', '.join(entity_names)}")
            except Exception as e:
                return MCPCallToolResult(content=f"实体提取失败: {e}", is_error=True)
        return MCPCallToolResult(content=f"未知工具: {request.name}", is_error=True)
