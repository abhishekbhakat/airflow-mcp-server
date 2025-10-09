"""Airflow-specific prompts for MCP server."""

from mcp.server.lowlevel import Server


def add_airflow_prompts(_server: Server, mode: str = "safe") -> None:  # pragma: no cover - placeholder
    """Add Airflow-specific prompts to the MCP server.

    Args:
        _server: MCP server instance
        mode: Server mode ("safe" or "unsafe")
    """
    pass
