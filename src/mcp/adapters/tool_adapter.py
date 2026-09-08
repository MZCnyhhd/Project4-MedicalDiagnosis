"""
模块名称: Tool MCP Adapter (工具 MCP 适配器)
功能描述:
    将诊断辅助工具封装为 MCP Server。
    目前主要提供结构化诊断生成工具。
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
from src.tools.common import generate_structured_diagnosis


class ToolMCPServer(MCPServer):
    """诊断工具 MCP Server"""

    def __init__(self):
        super().__init__("medical-tool-server")

    def list_resources(self) -> List[MCPResource]:
        return [
            MCPResource(
                uri="tool://diagnosis_engine",
                name="结构化诊断引擎",
                description="基于输入问题列表生成结构化诊断报告",
            ),
        ]

    def list_tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name="generate_structured_diagnosis",
                description="根据诊断问题列表生成包含 name/reason/suggestion 的结构化 JSON 诊断",
                input_schema={
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "reason": {"type": "string"},
                                "suggestion": {"type": "string"},
                            },
                        },
                    }
                },
            ),
        ]

    def read_resource(self, request: MCPReadResourceRequest) -> MCPReadResourceResult:
        if request.uri == "tool://diagnosis_engine":
            return MCPReadResourceResult(
                contents="结构化诊断引擎，可接收诊断问题列表并输出标准化的诊断建议。",
            )
        return MCPReadResourceResult(contents="", is_error=True)

    def call_tool(self, request: MCPCallToolRequest) -> MCPCallToolResult:
        if request.name == "generate_structured_diagnosis":
            try:
                issues = request.arguments.get("issues", [])
                result = generate_structured_diagnosis({"issues": issues})
                return MCPCallToolResult(content=str(result))
            except Exception as e:
                return MCPCallToolResult(content=f"工具执行失败: {e}", is_error=True)
        return MCPCallToolResult(content=f"未知工具: {request.name}", is_error=True)
