import logging
import sys
from pathlib import Path

import click

from airflow_mcp_server.server import serve


@click.command()
@click.option("-y", "--yaml-spec", type=Path, help="YAML spec file")
@click.option("-v", "--verbose", count=True)
def main(yaml_spec: Path | None, verbose: bool) -> None:
    """MCP server for Airflow"""
    import asyncio

    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)
    asyncio.run(serve(yaml_spec))


if __name__ == "__main__":
    main()
