"""
模块名称: MCP Server (MCP 服务端基类)
功能描述:
    定义 MCP Server 的标准接口，所有具体适配器需继承此类。
"""

from abc import ABC, abstractmethod
from typing import List

from src.mcp.protocol import (
    MCPResource,
    MCPTool,
    MCPReadResourceRequest,
    MCPReadResourceResult,
    MCPCallToolRequest,
    MCPCallToolResult,
)


class MCPServer(ABC):
    """MCP 服务端基类"""

    def __init__(self, server_name: str):
        self.server_name = server_name

    @abstractmethod
    def list_resources(self) -> List[MCPResource]:
        """列出 Server 提供的所有资源"""
        pass

    @abstractmethod
    def list_tools(self) -> List[MCPTool]:
        """列出 Server 提供的所有工具"""
        pass

    @abstractmethod
    def read_resource(self, request: MCPReadResourceRequest) -> MCPReadResourceResult:
        """读取指定资源"""
        pass

    @abstractmethod
    def call_tool(self, request: MCPCallToolRequest) -> MCPCallToolResult:
        """调用指定工具"""
        pass

    def initialize(self) -> dict:
        """初始化握手，返回 Server 元信息"""
        return {
            "server_name": self.server_name,
            "protocol_version": "2024-11-05",
            "capabilities": {
                "resources": {},
                "tools": {},
            },
        }
