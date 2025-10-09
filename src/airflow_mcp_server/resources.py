"""Airflow-specific resource registration helpers."""

from __future__ import annotations

from collections.abc import Callable

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents

from airflow_mcp_server.knowledge_resources import load_knowledge_resources


def register_resources(server: Server, resources_dir: str | None) -> None:
    resources = load_knowledge_resources(resources_dir)
    resource_map: dict[str, tuple[str, Callable[[], str], str]] = {
        uri: (title, reader, mime) for uri, title, reader, mime in resources
    }

    @server.list_resources()
    async def _list_resources(_: types.ListResourcesRequest | None = None) -> types.ListResourcesResult:
        items = [types.Resource(uri=uri, name=title, mimeType=mime) for uri, (title, _reader, mime) in resource_map.items()]
        return types.ListResourcesResult(resources=items)

    @server.read_resource()
    async def _read_resource(uri: str) -> list[ReadResourceContents]:
        if uri not in resource_map:
            raise ValueError(f"Unknown resource '{uri}'")

        _title, reader, mime = resource_map[uri]
        content = reader()
        return [ReadResourceContents(content=str(content), mime_type=mime)]
