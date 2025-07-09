import asyncio
import logging
import os
import sys

import click

from airflow_mcp_server.config import AirflowConfig
from airflow_mcp_server.server_safe import serve as serve_safe
from airflow_mcp_server.server_unsafe import serve as serve_unsafe


@click.command()
@click.option("-v", "--verbose", count=True, help="Increase verbosity")
@click.option("--safe", "-s", is_flag=True, help="Use only read-only tools")
@click.option("--unsafe", "-u", is_flag=True, help="Use all tools (default)")
@click.option("--static-tools", is_flag=True, help="Use static tools instead of hierarchical discovery")
@click.option("--base-url", help="Airflow API base URL")
@click.option("--auth-token", help="Authentication token (JWT)")
@click.option("--http", is_flag=True, help="Use HTTP (Streamable HTTP) transport instead of stdio")
@click.option("--sse", is_flag=True, help="Use Server-Sent Events transport (deprecated, use --http instead)")
@click.option("--port", type=int, default=3000, help="Port to run HTTP/SSE server on (default: 3000)")
@click.option("--host", type=str, default="localhost", help="Host to bind HTTP/SSE server to (default: localhost)")
@click.help_option("-h", "--help")
def main(
    verbose: int,
    safe: bool,
    unsafe: bool,
    static_tools: bool,
    base_url: str | None = None,
    auth_token: str | None = None,
    http: bool = False,
    sse: bool = False,
    port: int = 3000,
    host: str = "localhost",
) -> None:
    """MCP server for Airflow"""
    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)

    if http and sse:
        raise click.UsageError("Cannot specify both --http and --sse")
    if sse:
        click.echo("Warning: SSE transport is deprecated. Consider using --http instead.", err=True)

    config_base_url = os.environ.get("AIRFLOW_BASE_URL") or base_url
    config_auth_token = os.environ.get("AUTH_TOKEN") or auth_token

    try:
        config = AirflowConfig(base_url=config_base_url, auth_token=config_auth_token)
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    if http or sse:
        transport_type = "streamable-http" if http else "sse"
        transport_config = {"port": port, "host": host}
    else:
        transport_type = "stdio"
        transport_config = {}

    if safe and unsafe:
        raise click.UsageError("Options --safe and --unsafe are mutually exclusive")
    elif safe:
        asyncio.run(serve_safe(config, static_tools=static_tools, transport=transport_type, **transport_config))
    elif unsafe:
        asyncio.run(serve_unsafe(config, static_tools=static_tools, transport=transport_type, **transport_config))
    else:
        asyncio.run(serve_unsafe(config, static_tools=static_tools, transport=transport_type, **transport_config))


if __name__ == "__main__":
    main()
