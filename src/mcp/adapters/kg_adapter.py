"""
模块名称: KG MCP Adapter (知识图谱 MCP 适配器)
功能描述:
    将 Neo4j 知识图谱服务封装为 MCP Server。
    提供疾病、症状、检查、治疗等图谱资源和查询工具。
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
from src.services.kg import get_kg


class KnowledgeGraphMCPServer(MCPServer):
    """知识图谱 MCP Server"""

    def __init__(self):
        super().__init__("medical-kg-server")
        self._kg = get_kg()

    def list_resources(self) -> List[MCPResource]:
        return [
            MCPResource(uri="kg://diseases", name="疾病图谱", description="所有疾病节点及关联关系"),
            MCPResource(uri="kg://symptoms", name="症状图谱", description="症状与疾病的关联"),
            MCPResource(uri="kg://examinations", name="检查图谱", description="检查项目与疾病的关联"),
        ]

    def list_tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name="get_disease_context",
                description="获取指定疾病的完整上下文（症状、检查、治疗、相关疾病）",
                input_schema={"disease_name": {"type": "string"}},
            ),
            MCPTool(
                name="find_diseases_by_symptoms",
                description="根据症状列表查找可能的疾病",
                input_schema={"symptoms": {"type": "array", "items": {"type": "string"}}},
            ),
        ]

    def read_resource(self, request: MCPReadResourceRequest) -> MCPReadResourceResult:
        uri = request.uri
        if uri == "kg://diseases":
            return MCPReadResourceResult(contents="知识图谱疾病节点资源，可通过工具查询具体疾病详情。")
        elif uri == "kg://symptoms":
            return MCPReadResourceResult(contents="知识图谱症状节点资源。")
        elif uri == "kg://examinations":
            return MCPReadResourceResult(contents="知识图谱检查节点资源。")
        return MCPReadResourceResult(contents="", is_error=True)

    def call_tool(self, request: MCPCallToolRequest) -> MCPCallToolResult:
        if not self._kg:
            return MCPCallToolResult(content="知识图谱未初始化", is_error=True)
        try:
            if request.name == "get_disease_context":
                disease = request.arguments.get("disease_name", "")
                result = self._kg.get_disease_full_context(disease)
                content = str(result) if result else f"未找到疾病: {disease}"
                return MCPCallToolResult(content=content)
            elif request.name == "find_diseases_by_symptoms":
                symptoms = request.arguments.get("symptoms", [])
                matches = self._kg.find_diseases_by_symptoms(symptoms, limit=5)
                names = [m.get("disease_name", "") for m in matches]
                return MCPCallToolResult(content=f"可能疾病: {', '.join(names)}")
            else:
                return MCPCallToolResult(content=f"未知工具: {request.name}", is_error=True)
        except Exception as e:
            return MCPCallToolResult(content=f"图谱查询异常: {e}", is_error=True)
