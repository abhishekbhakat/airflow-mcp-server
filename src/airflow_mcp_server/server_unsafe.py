import logging

import httpx
from fastmcp import FastMCP

from airflow_mcp_server.config import AirflowConfig
from airflow_mcp_server.hierarchical_manager import HierarchicalToolManager
from airflow_mcp_server.prompts import add_airflow_prompts
from airflow_mcp_server.resources import add_airflow_resources

logger = logging.getLogger(__name__)


async def serve(config: AirflowConfig) -> None:
    """Start MCP server in unsafe mode (all operations).

    Args:
        config: Configuration object with auth and URL settings
    """
    # Create authenticated HTTP client
    client = httpx.AsyncClient(base_url=config.base_url, headers={"Authorization": f"Bearer {config.auth_token}"}, timeout=30.0)

    # Fetch OpenAPI spec
    try:
        response = await client.get("/openapi.json")
        response.raise_for_status()
        openapi_spec = response.json()
    except Exception as e:
        logger.error("Failed to fetch OpenAPI spec: %s", e)
        await client.aclose()
        raise

    # Create FastMCP server without auto-generated tools (we'll use hierarchical manager)
    mcp = FastMCP("Airflow MCP Server (Unsafe Mode)")

    # Initialize hierarchical tool manager with all methods allowed
    _ = HierarchicalToolManager(
        mcp=mcp,
        openapi_spec=openapi_spec,
        client=client,
        allowed_methods={"GET", "POST", "PUT", "DELETE", "PATCH"},  # All operations
    )

    # Add Airflow-specific resources and prompts
    add_airflow_resources(mcp, config, mode="unsafe")
    add_airflow_prompts(mcp, mode="unsafe")

    # Run the FastMCP server
    try:
        await mcp.run_async()
    except Exception as e:
        logger.error("Server error: %s", e)
        await client.aclose()
        raise
