import asyncio

from airflow_mcp_server.tools.tool_manager import get_airflow_tools

# Get tools with their parameters
tools = asyncio.run(get_airflow_tools(mode="safe"))
TOOLS = {tool.name: {"description": tool.description, "parameters": tool.inputSchema} for tool in tools}
