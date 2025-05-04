import logging
from typing import Any

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Prompt, Resource, ResourceTemplate, TextContent, Tool

from airflow_mcp_server.config import AirflowConfig
from airflow_mcp_server.tools.tool_manager import get_airflow_tools, get_tool

logger = logging.getLogger(__name__)


async def serve(config: AirflowConfig) -> None:
    """Start MCP server in safe mode (read-only operations).

    Args:
        config: Configuration object with auth and URL settings
    """
    server = Server("airflow-mcp-server-safe")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        try:
            return await get_airflow_tools(config, mode="safe")
        except Exception as e:
            logger.error("Failed to list tools: %s", e)
            raise

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List available resources (returns empty list)."""
        logger.info("Resources list requested - returning empty list")
        return []

    @server.list_resource_templates()
    async def list_resource_templates() -> list[ResourceTemplate]:
        """List available resource templates (returns empty list)."""
        logger.info("Resource templates list requested - returning empty list")
        return []

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        """List available prompts (returns empty list)."""
        logger.info("Prompts list requested - returning empty list")
        return []

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if not name.startswith("get_"):
                raise ValueError("Only GET operations allowed in safe mode")
            tool = await get_tool(config, name)
            async with tool.client:
                result = await tool.run(body=arguments)
            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            logger.error("Tool execution failed: %s", e)
            raise

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        try:
            await server.run(read_stream, write_stream, options, raise_exceptions=True)
        except anyio.BrokenResourceError:
            logger.error("BrokenResourceError: Stream was closed unexpectedly. Exiting gracefully.")
        except Exception as e:
            logger.error(f"Unexpected error in server.run: {e}")
            raise
