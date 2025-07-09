import logging
from typing import Literal

import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap

from airflow_mcp_server.config import AirflowConfig
from airflow_mcp_server.hierarchical_manager import HierarchicalToolManager
from airflow_mcp_server.prompts import add_airflow_prompts
from airflow_mcp_server.resources import add_airflow_resources

logger = logging.getLogger(__name__)


async def serve(config: AirflowConfig, static_tools: bool = False, transport: Literal["stdio", "streamable-http", "sse"] = "stdio", **transport_kwargs) -> None:
    """Start MCP server in safe mode (read-only operations).

    Args:
        config: Configuration object with auth and URL settings
        static_tools: If True, use static tools instead of hierarchical discovery
        transport: Transport type ("stdio", "streamable-http", "sse")
        **transport_kwargs: Additional transport configuration (port, host, etc.)
    """

    if not config.base_url:
        raise ValueError("base_url is required")
    if not config.auth_token:
        raise ValueError("auth_token is required")

    client = httpx.AsyncClient(base_url=config.base_url, headers={"Authorization": f"Bearer {config.auth_token}"}, timeout=30.0)

    try:
        response = await client.get("/openapi.json")
        response.raise_for_status()
        openapi_spec = response.json()
    except Exception as e:
        logger.error("Failed to fetch OpenAPI spec: %s", e)
        await client.aclose()
        raise

    if static_tools:
        route_maps = [RouteMap(methods=["GET"], mcp_type=MCPType.TOOL)]
        mcp = FastMCP.from_openapi(openapi_spec=openapi_spec, client=client, name="Airflow MCP Server (Safe Mode - Static Tools)", route_maps=route_maps)
    else:
        mcp = FastMCP("Airflow MCP Server (Safe Mode)")

        _ = HierarchicalToolManager(
            mcp=mcp,
            openapi_spec=openapi_spec,
            client=client,
            allowed_methods={"GET"},
        )

    add_airflow_resources(mcp, config, mode="safe")
    add_airflow_prompts(mcp, mode="safe")

    try:
        if transport in ["streamable-http", "sse"]:
            await mcp.run_async(transport=transport, **transport_kwargs)
        else:
            await mcp.run_async()
    except Exception as e:
        logger.error("Server error: %s", e)
        await client.aclose()
        raise
