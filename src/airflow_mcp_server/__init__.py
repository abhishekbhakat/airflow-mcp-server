import asyncio
import logging
import sys

import click

from airflow_mcp_server.server_safe import serve as serve_safe
from airflow_mcp_server.server_unsafe import serve as serve_unsafe


@click.command()
@click.option("-v", "--verbose", count=True, help="Increase verbosity")
@click.option("--safe", "-s", is_flag=True, help="Use only read-only tools")
@click.option("--unsafe", "-u", is_flag=True, help="Use all tools (default)")
def main(verbose: int, safe: bool, unsafe: bool) -> None:
    """MCP server for Airflow"""
    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)

    if safe and unsafe:
        raise click.UsageError("Options --safe and --unsafe are mutually exclusive")

    if safe:
        asyncio.run(serve_safe())
    else:  # Default to unsafe mode
        asyncio.run(serve_unsafe())


if __name__ == "__main__":
    main()
