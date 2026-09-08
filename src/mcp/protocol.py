"""
模块名称: MCP Protocol (MCP 协议定义)
功能描述:
    定义简化版 MCP 协议的数据结构和消息类型。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MCPResource:
    """MCP 资源定义"""
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPReadResourceRequest:
    """读取资源请求"""
    uri: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPReadResourceResult:
    """读取资源结果"""
    contents: str
    mime_type: str = "text/plain"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPCallToolRequest:
    """调用工具请求"""
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPCallToolResult:
    """调用工具结果"""
    content: str
    is_error: bool = False
