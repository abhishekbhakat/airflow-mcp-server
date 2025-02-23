import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from airflow_mcp_server.tools.tool_manager import get_airflow_tools, get_tool

logger = logging.getLogger(__name__)


async def serve() -> None:
    """Start MCP server in safe mode (read-only operations)."""
    required_vars = ["AIRFLOW_BASE_URL", "AUTH_TOKEN"]
    if not all(var in os.environ for var in required_vars):
        raise ValueError(f"Missing required environment variables: {required_vars}")

    server = Server("airflow-mcp-server-safe")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        try:
            return await get_airflow_tools(mode="safe")
        except Exception as e:
            logger.error("Failed to list tools: %s", e)
            raise

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if not name.startswith("get_"):
                raise ValueError("Only GET operations allowed in safe mode")
            tool = await get_tool(name)
            async with tool.client:
                result = await tool.run(body=arguments)
            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            logger.error("Tool execution failed: %s", e)
            raise

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
