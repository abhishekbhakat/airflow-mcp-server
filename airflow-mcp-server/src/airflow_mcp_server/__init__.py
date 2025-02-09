import logging
import sys
from pathlib import Path

import click

from airflow_mcp_server.server import serve


@click.command()
@click.option("--working-dir", "-w", type=Path, help="Working directory path")
@click.option("-v", "--verbose", count=True)
def main(working_dir: Path | None, verbose: bool) -> None:
    """MCP Code Assist Server - Code operations for MCP"""
    import asyncio

    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)
    asyncio.run(serve(working_dir))


if __name__ == "__main__":
    main()
