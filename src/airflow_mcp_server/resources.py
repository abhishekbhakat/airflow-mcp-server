"""Airflow-specific resource registration helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from pydantic import AnyUrl

from airflow_mcp_server.knowledge_resources import load_knowledge_resources


def register_resources(server: Server, resources_dir: str | None) -> None:
    resources = load_knowledge_resources(resources_dir)
    resource_map: dict[str, tuple[str, Callable[[], str], str]] = {
        uri: (title, reader, mime) for uri, title, reader, mime in resources
    }

    @server.list_resources()
    async def _list_resources(_: types.ListResourcesRequest | None = None) -> types.ListResourcesResult:
        items = [
            types.Resource(uri=cast(AnyUrl, uri), name=title, mimeType=mime)
            for uri, (title, _reader, mime) in resource_map.items()
        ]
        return types.ListResourcesResult(resources=items)

    @server.read_resource()
    async def _read_resource(uri: AnyUrl) -> list[ReadResourceContents]:
        uri_str = str(uri)
        if uri_str not in resource_map:
            raise ValueError(f"Unknown resource '{uri_str}'")

        _title, reader, mime = resource_map[uri_str]
        content = reader()
        return [ReadResourceContents(content=str(content), mime_type=mime)]
