import logging
import os

from mcp.types import Tool

from airflow_mcp_server.client.airflow_client import AirflowClient
from airflow_mcp_server.parser.operation_parser import OperationParser
from airflow_mcp_server.tools.airflow_tool import AirflowTool

logger = logging.getLogger(__name__)

_tools_cache: dict[str, AirflowTool] = {}
_client: AirflowClient | None = None


def get_airflow_tools() -> list[Tool]:
    """Get list of all available Airflow tools.

    Returns:
        List of MCP Tool objects representing available operations

    Raises:
        ValueError: If required environment variables are missing
    """
    global _tools_cache, _client

    if not _tools_cache:
        required_vars = ["OPENAPI_SPEC", "AIRFLOW_BASE_URL", "AUTH_TOKEN"]
        if not all(var in os.environ for var in required_vars):
            raise ValueError(f"Missing required environment variables: {required_vars}")

        # Initialize client if not exists
        if not _client:
            _client = AirflowClient(spec_path=os.environ["OPENAPI_SPEC"], base_url=os.environ["AIRFLOW_BASE_URL"], auth_token=os.environ["AUTH_TOKEN"])

        try:
            # Create parser
            parser = OperationParser(os.environ["OPENAPI_SPEC"])

            # Generate tools for each operation
            for operation_id in parser.get_operations():
                operation_details = parser.parse_operation(operation_id)
                tool = AirflowTool(operation_details, _client)
                _tools_cache[operation_id] = tool

        except Exception as e:
            logger.error("Failed to initialize tools: %s", e)
            raise

    # Convert to MCP Tool format
    return [
        Tool(
            name=operation_id,
            description=tool.operation.operation_id,
            inputSchema=tool.operation.request_body.model_json_schema() if tool.operation.request_body else None,
        )
        for operation_id, tool in _tools_cache.items()
    ]


def get_tool(name: str) -> AirflowTool:
    """Get specific tool by name.

    Args:
        name: Tool/operation name

    Returns:
        AirflowTool instance

    Raises:
        KeyError: If tool not found
    """
    if name not in _tools_cache:
        # Ensure cache is populated
        get_airflow_tools()

    return _tools_cache[name]
