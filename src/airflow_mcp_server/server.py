import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from airflow_mcp_server.config import AirflowConfig
from airflow_mcp_server.tools.tool_manager import get_airflow_tools, get_tool

# ===========THIS IS FOR DEBUGGING WITH MCP INSPECTOR===================
# import sys
# Configure root logger to stderr
# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler(sys.stderr)])

# Disable Uvicorn's default handlers
# logging.getLogger("uvicorn.error").handlers = []
# logging.getLogger("uvicorn.access").handlers = []
# ======================================================================
logger = logging.getLogger(__name__)


async def serve(config: AirflowConfig) -> None:
    """Start MCP server.

    Args:
        config: Configuration object with auth and URL settings
    """
    server = Server("airflow-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        try:
            return await get_airflow_tools(config)
        except Exception as e:
            logger.error("Failed to list tools: %s", e)
            raise

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            tool = await get_tool(config, name)
            async with tool.client:
                result = await tool.run(body=arguments)
            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            logger.error("Tool execution failed: %s", e)
            raise

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
