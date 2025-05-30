"""Airflow-specific prompts for MCP server."""

from fastmcp import FastMCP


def add_airflow_prompts(mcp: FastMCP, mode: str = "safe") -> None:
    """Add Airflow-specific prompts to the MCP server.

    Args:
        mcp: FastMCP server instance
        mode: Server mode ("safe" or "unsafe")
    """
    # No prompts - return empty list
    pass
