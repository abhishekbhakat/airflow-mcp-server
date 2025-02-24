import logging
import os
from importlib import resources

from mcp.types import Tool

from airflow_mcp_server.client.airflow_client import AirflowClient
from airflow_mcp_server.parser.operation_parser import OperationParser
from airflow_mcp_server.tools.airflow_tool import AirflowTool

logger = logging.getLogger(__name__)

_tools_cache: dict[str, AirflowTool] = {}


def _initialize_client() -> AirflowClient:
    """Initialize Airflow client with environment variables or embedded spec.

    Returns:
        AirflowClient instance

    Raises:
        ValueError: If required environment variables are missing or default spec is not found
    """
    spec_path = os.environ.get("OPENAPI_SPEC")
    if not spec_path:
        # Fallback to embedded v1.yaml
        try:
            with resources.files("airflow_mcp_server.resources").joinpath("v1.yaml").open("rb") as f:
                spec_path = f.name
                logger.info("OPENAPI_SPEC not set; using embedded v1.yaml from %s", spec_path)
        except Exception as e:
            raise ValueError("Default OpenAPI spec not found in package resources") from e

    required_vars = ["AIRFLOW_BASE_URL", "AUTH_TOKEN"]
    missing_vars = [var for var in required_vars if var not in os.environ]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")

    return AirflowClient(spec_path=spec_path, base_url=os.environ["AIRFLOW_BASE_URL"], auth_token=os.environ["AUTH_TOKEN"])


async def _initialize_tools() -> None:
    """Initialize tools cache with Airflow operations.

    Raises:
        ValueError: If initialization fails
    """
    global _tools_cache

    try:
        client = _initialize_client()
        spec_path = os.environ.get("OPENAPI_SPEC")
        if not spec_path:
            with resources.files("airflow_mcp_server.resources").joinpath("v1.yaml").open("rb") as f:
                spec_path = f.name
        parser = OperationParser(spec_path)

        # Generate tools for each operation
        for operation_id in parser.get_operations():
            operation_details = parser.parse_operation(operation_id)
            tool = AirflowTool(operation_details, client)
            _tools_cache[operation_id] = tool

    except Exception as e:
        logger.error("Failed to initialize tools: %s", e)
        _tools_cache.clear()
        raise ValueError(f"Failed to initialize tools: {e}") from e


async def get_airflow_tools(mode: str = "unsafe") -> list[Tool]:
    """Get list of available Airflow tools based on mode.

    Args:
        mode: "safe" for GET operations only, "unsafe" for all operations (default)

    Returns:
        List of MCP Tool objects representing available operations

    Raises:
        ValueError: If initialization fails
    """
    if not _tools_cache:
        await _initialize_tools()

    tools = []
    for operation_id, tool in _tools_cache.items():
        try:
            # Skip non-GET operations in safe mode
            if mode == "safe" and not tool.operation.method.lower() == "get":
                continue
            schema = tool.operation.input_model.model_json_schema()
            tools.append(
                Tool(
                    name=operation_id,
                    description=tool.operation.operation_id,
                    inputSchema=schema,
                )
            )
        except Exception as e:
            logger.error("Failed to create tool schema for %s: %s", operation_id, e)
            continue

    return tools


async def get_tool(name: str) -> AirflowTool:
    """Get specific tool by name.

    Args:
        name: Tool/operation name

    Returns:
        AirflowTool instance

    Raises:
        KeyError: If tool not found
        ValueError: If tool initialization fails
    """
    if not _tools_cache:
        await _initialize_tools()

    if name not in _tools_cache:
        raise KeyError(f"Tool {name} not found")

    return _tools_cache[name]
