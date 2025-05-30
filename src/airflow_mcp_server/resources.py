"""Airflow-specific resources for MCP server."""

import logging

from fastmcp import FastMCP

from airflow_mcp_server.config import AirflowConfig

logger = logging.getLogger(__name__)


def add_airflow_resources(mcp: FastMCP, config: AirflowConfig, mode: str = "safe") -> None:
    """Add Airflow-specific resources to the MCP server.

    Args:
        mcp: FastMCP server instance
        config: Airflow configuration
        mode: Server mode ("safe" or "unsafe")
    """

    # No resources - return empty list
