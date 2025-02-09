import os
from enum import Enum
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from airflow_mcp_server.tools.models import ListDags
from airflow_mcp_server.tools.tool_manager import get_airflow_dag_tools


class AirflowAPITools(str, Enum):
    # DAG Operations
    LIST_DAGS = "list_dags"


async def process_instruction(instruction: dict[str, Any]) -> dict[str, Any]:
    dag_tools = get_airflow_dag_tools()

    try:
        match instruction["type"]:
            case "list_dags":
                return {"dags": await dag_tools.list_dags()}
            case _:
                return {"message": "Invalid instruction type"}
    except Exception as e:
        return {"error": str(e)}


async def serve() -> None:
    server = Server("airflow-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = [
            # DAG Operations
            Tool(
                name=AirflowAPITools.LIST_DAGS,
                description="Lists all DAGs in Airflow",
                inputSchema=ListDags.model_json_schema(),
            ),
        ]
        if "AIRFLOW_BASE_URL" in os.environ and "AUTH_TOKEN" in os.environ:
            return tools
        else:
            return []

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        dag_tools = get_airflow_dag_tools()

        match name:
            case AirflowAPITools.LIST_DAGS:
                result = await dag_tools.list_dags()
                return [TextContent(type="text", text=result)]
            case _:
                raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        server.run(read_stream, write_stream, options, raise_exceptions=True)
