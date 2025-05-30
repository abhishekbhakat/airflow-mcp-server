import logging
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

from airflow_mcp_server.config import AirflowConfig
from airflow_mcp_server.resources import add_airflow_resources
from airflow_mcp_server.prompts import add_airflow_prompts

logger = logging.getLogger(__name__)


async def serve(config: AirflowConfig) -> None:
    """Start MCP server in safe mode (read-only operations).

    Args:
        config: Configuration object with auth and URL settings
    """
    # Create authenticated HTTP client
    client = httpx.AsyncClient(
        base_url=config.base_url,
        headers={"Authorization": f"Bearer {config.auth_token}"},
        timeout=30.0
    )

    # Fetch OpenAPI spec
    try:
        response = await client.get("/openapi.json")
        response.raise_for_status()
        openapi_spec = response.json()
    except Exception as e:
        logger.error("Failed to fetch OpenAPI spec: %s", e)
        await client.aclose()
        raise

    # Create FastMCP server with safe mode (GET operations only)
    mcp = FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        route_maps=[
            # Only allow GET operations in safe mode
            RouteMap(methods=["GET"], mcp_type=MCPType.TOOL),
            # Exclude all other methods
            RouteMap(methods=["POST", "PUT", "DELETE", "PATCH"], mcp_type=MCPType.EXCLUDE),
        ]
    )

    # Add Airflow-specific resources and prompts
    add_airflow_resources(mcp, config, mode="safe")
    add_airflow_prompts(mcp, mode="safe")


    # Run the FastMCP server
    try:
        await mcp.run_async()
    except Exception as e:
        logger.error("Server error: %s", e)
        await client.aclose()
        raise