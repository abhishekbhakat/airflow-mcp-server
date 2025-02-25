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
@click.option("--base-url", help="Airflow API base URL")
@click.option("--spec-path", help="Path to OpenAPI spec file")
@click.option("--auth-token", help="Authentication token")
@click.option("--cookie", help="Session cookie")
def main(verbose: int, safe: bool, unsafe: bool, base_url: str = None, spec_path: str = None, auth_token: str = None, cookie: str = None) -> None:
    """MCP server for Airflow"""
    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)

    # Read environment variables with proper precedence
    # Environment variables take precedence over CLI arguments
    config_base_url = os.environ.get("AIRFLOW_BASE_URL") or base_url
    config_spec_path = os.environ.get("OPENAPI_SPEC") or spec_path
    config_auth_token = os.environ.get("AUTH_TOKEN") or auth_token
    config_cookie = os.environ.get("COOKIE") or cookie

    # Initialize configuration
    try:
        config = AirflowConfig(base_url=config_base_url, spec_path=config_spec_path, auth_token=config_auth_token, cookie=config_cookie)
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)

    # Determine server mode with proper precedence
    if safe and unsafe:
        # CLI argument validation
        raise click.UsageError("Options --safe and --unsafe are mutually exclusive")
    elif safe:
        # CLI argument for safe mode
        asyncio.run(serve_safe(config))
    else:
        # Default to unsafe mode
        asyncio.run(serve_unsafe(config))


if __name__ == "__main__":
    main()
