"""
模块名称: MCP Client (MCP 客户端)
功能描述:
    Agent 侧的 MCP 消费端，统一管理多个 MCP Server 的连接和资源发现。
"""

from typing import Dict, List, Optional

from src.mcp.server import MCPServer
from src.mcp.protocol import (
    MCPResource,
    MCPTool,
    MCPReadResourceRequest,
    MCPReadResourceResult,
    MCPCallToolRequest,
    MCPCallToolResult,
)
from src.services.logging import log_info, log_warn


class MCPClient:
    """MCP 客户端（支持多 Server 管理）"""

    def __init__(self):
        self._servers: Dict[str, MCPServer] = {}

    def connect(self, server: MCPServer) -> "MCPClient":
        """连接并注册一个 MCP Server"""
        info = server.initialize()
        name = info.get("server_name", "unknown")
        self._servers[name] = server
        log_info(f"[MCPClient] 已连接 Server: {name}")
        return self

    def disconnect(self, server_name: str):
        """断开指定 Server"""
        if server_name in self._servers:
            del self._servers[server_name]
            log_info(f"[MCPClient] 已断开 Server: {server_name}")

    def list_all_resources(self) -> List[MCPResource]:
        """列出所有已连接 Server 的资源"""
        resources = []
        for server in self._servers.values():
            resources.extend(server.list_resources())
        return resources

    def list_all_tools(self) -> List[MCPTool]:
        """列出所有已连接 Server 的工具"""
        tools = []
        for server in self._servers.values():
            tools.extend(server.list_tools())
        return tools

    def read_resource(self, server_name: str, uri: str, parameters: dict = None) -> Optional[MCPReadResourceResult]:
        """从指定 Server 读取资源"""
        server = self._servers.get(server_name)
        if not server:
            log_warn(f"[MCPClient] Server 未连接: {server_name}")
            return None
        req = MCPReadResourceRequest(uri=uri, parameters=parameters or {})
        return server.read_resource(req)

    def call_tool(self, server_name: str, tool_name: str, arguments: dict = None) -> Optional[MCPCallToolResult]:
        """在指定 Server 上调用工具"""
        server = self._servers.get(server_name)
        if not server:
            log_warn(f"[MCPClient] Server 未连接: {server_name}")
            return None
        req = MCPCallToolRequest(name=tool_name, arguments=arguments or {})
        return server.call_tool(req)

    def discover_and_read(self, uri_keyword: str) -> List[MCPReadResourceResult]:
        """
        跨所有 Server 搜索包含关键字的 URI 并读取资源。
        简化版资源发现，适合医疗诊断中按疾病名检索场景。
        """
        results = []
        for name, server in self._servers.items():
            for res in server.list_resources():
                if uri_keyword in res.uri or uri_keyword in res.name:
                    req = MCPReadResourceRequest(uri=res.uri)
                    result = server.read_resource(req)
                    results.append(result)
        return results
