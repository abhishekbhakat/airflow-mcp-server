from typing import Literal

from airflow_mcp_server.config import AirflowConfig
from airflow_mcp_server.server_safe import _serve_airflow


async def serve(
    config: AirflowConfig,
    static_tools: bool = False,
    resources_dir: str | None = None,
    transport: Literal["stdio", "streamable-http", "sse"] = "stdio",
    **transport_kwargs,
) -> None:
    """Start MCP server in unsafe mode (read/write operations)."""

    await _serve_airflow(
        config=config,
        allowed_methods={"GET", "POST", "PUT", "DELETE", "PATCH"},
        mode_label="Unsafe Mode",
        static_tools=static_tools,
        resources_dir=resources_dir,
        transport=transport,
        transport_kwargs=transport_kwargs,
    )
