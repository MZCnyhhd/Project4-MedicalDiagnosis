"""
模块名称: MCP Bootstrap (MCP 启动器)
功能描述:
    一键初始化 MCP 客户端并连接所有医疗数据源 Server。
    可作为 app.py 启动时的可选增强步骤。

用法示例:
    from src.mcp.bootstrap import create_medical_mcp_client
    client = create_medical_mcp_client()
    # 使用 client 读取资源或调用工具
    result = client.call_tool("medical-rag-server", "hybrid_retrieve", {"report": "患者报告..."})
"""

from src.mcp.client import MCPClient
from src.mcp.adapters import RAGMCPServer, KnowledgeGraphMCPServer, ToolMCPServer


def create_medical_mcp_client() -> MCPClient:
    """
    创建并配置医疗 MCP 客户端，连接所有内置 Server。
    :return: 配置好的 MCPClient 实例
    """
    client = MCPClient()
    client.connect(RAGMCPServer())
    client.connect(KnowledgeGraphMCPServer())
    client.connect(ToolMCPServer())
    return client
