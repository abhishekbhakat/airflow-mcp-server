import asyncio
from typing import Any

import pytest
from mcp import types
from mcp.server.lowlevel import Server

from airflow_mcp_plugin.toolset import AirflowOpenAPIToolset


@pytest.fixture
def sample_spec() -> dict[str, Any]:
    return {
        "openapi": "3.0.0",
        "paths": {
            "/items/{item_id}": {
                "parameters": [
                    {
                        "name": "item_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "get_item",
                    "responses": {"200": {"description": "ok"}},
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                        },
                        {
                            "name": "exclude_stale",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "boolean"},
                        },
                        {
                            "name": "order_by",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        {
                            "name": "tags_match_mode",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "nullable": True},
                        },
                    ],
                },
                "post": {
                    "operationId": "create_item",
                    "responses": {"200": {"description": "ok"}},
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "value": {"type": "integer"},
                                    },
                                    "required": ["name"],
                                }
                            }
                        }
                    },
                },
            }
        },
    }


def test_toolset_respects_safe_mode(sample_spec: dict[str, Any]) -> None:
    toolset = AirflowOpenAPIToolset(sample_spec, allow_mutations=False)
    tool_names = [tool.name for tool in toolset.list_tools()]
    assert tool_names == ["get_item"]


def test_toolset_includes_mutations_when_allowed(sample_spec: dict[str, Any]) -> None:
    toolset = AirflowOpenAPIToolset(sample_spec, allow_mutations=True)
    tool_names = sorted(tool.name for tool in toolset.list_tools())
    assert tool_names == ["create_item", "get_item"]


def test_input_model_accepts_optional_values(sample_spec: dict[str, Any]) -> None:
    toolset = AirflowOpenAPIToolset(sample_spec, allow_mutations=False)
    _, details = toolset.get_tool("get_item")

    payload = {
        "item_id": "alpha",
        "limit": 50,
        "exclude_stale": True,
        "order_by": ["dag_id"],
        "tags_match_mode": None,
    }

    model_instance = details.input_model(**payload)
    data = model_instance.model_dump()

    assert data["limit"] == 50
    assert data["exclude_stale"] is True
    assert data["order_by"] == ["dag_id"]
    assert data.get("tags_match_mode") is None


@pytest.mark.asyncio
async def test_call_tool_uses_aiohttp_session(sample_spec: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        def __init__(self) -> None:
            self.status = 200
            self.headers = {"content-type": "application/json"}
            self._body = b"{\"ok\": true}"

        async def read(self) -> bytes:
            await asyncio.sleep(0)
            return self._body

        async def __aenter__(self) -> "DummyResponse":
            return self

        async def __aexit__(self, *exc_info) -> None:
            return None

    class DummySession:
        def __init__(self, *args, **kwargs) -> None:
            self.captured_request: dict[str, Any] | None = None

        async def __aenter__(self) -> "DummySession":
            return self

        async def __aexit__(self, *exc_info) -> None:
            return None

        def request(self, method: str, path: str, params: dict[str, Any] | None, json: dict[str, Any] | None):
            self.captured_request = {
                "method": method,
                "path": path,
                "params": params,
                "json": json,
            }
            return DummyResponse()

    dummy_session = DummySession()

    monkeypatch.setattr("airflow_mcp_plugin.toolset.aiohttp.ClientSession", lambda *args, **kwargs: dummy_session)

    toolset = AirflowOpenAPIToolset(sample_spec, allow_mutations=False)
    arguments = {
        "item_id": "alpha",
        "limit": 5,
        "exclude_stale": True,
        "order_by": ["dag_id"],
    }

    result = await toolset.call_tool("get_item", arguments, "http://example.com", "token")

    assert result == ([], {"ok": True})
    assert dummy_session.captured_request == {
        "method": "GET",
        "path": "/items/alpha",
        "params": {"limit": "5", "exclude_stale": "true", "order_by": ["dag_id"]},
        "json": None,
    }


@pytest.mark.asyncio
async def test_call_tool_falls_back_to_text_content(monkeypatch: pytest.MonkeyPatch, sample_spec: dict[str, Any]) -> None:
    class DummyResponse:
        def __init__(self) -> None:
            self.status = 200
            self.headers = {"content-type": "text/plain"}
            self._body = b"plain text"

        async def read(self) -> bytes:
            await asyncio.sleep(0)
            return self._body

        async def __aenter__(self) -> "DummyResponse":
            return self

        async def __aexit__(self, *exc_info) -> None:
            return None

    class DummySession:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "DummySession":
            return self

        async def __aexit__(self, *exc_info) -> None:
            return None

        def request(self, *args, **kwargs):
            return DummyResponse()

    monkeypatch.setattr("airflow_mcp_plugin.toolset.aiohttp.ClientSession", lambda *args, **kwargs: DummySession())

    toolset = AirflowOpenAPIToolset(sample_spec, allow_mutations=False)
    result = await toolset.call_tool("get_item", {"item_id": "alpha"}, "http://example.com", "token")

    assert result == [types.TextContent(type="text", text="plain text")]


@pytest.mark.asyncio
async def test_call_tool_result_incompatible_with_server(monkeypatch: pytest.MonkeyPatch, sample_spec: dict[str, Any]) -> None:
    class DummyResponse:
        def __init__(self) -> None:
            self.status = 200
            self.headers = {"content-type": "application/json"}
            self._body = b'{"ok": true}'

        async def read(self) -> bytes:
            await asyncio.sleep(0)
            return self._body

        async def __aenter__(self) -> "DummyResponse":
            return self

        async def __aexit__(self, *exc_info) -> None:
            return None

    class DummySession:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "DummySession":
            return self

        async def __aexit__(self, *exc_info) -> None:
            return None

        def request(self, *args, **kwargs):
            return DummyResponse()

    monkeypatch.setattr("airflow_mcp_plugin.toolset.aiohttp.ClientSession", lambda *args, **kwargs: DummySession())

    toolset = AirflowOpenAPIToolset(sample_spec, allow_mutations=False)

    server = Server(name="test")

    @server.list_tools()
    async def _list_tools():
        return toolset.list_tools()

    @server.call_tool()
    async def _call_tool(tool_name: str, arguments: dict[str, Any]):
        return await toolset.call_tool(tool_name, arguments, "http://example.com", "token")

    request = types.CallToolRequest.model_validate(
        {
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "tools/call",
            "params": {"name": "get_item", "arguments": {"item_id": "alpha"}},
        }
    )

    handler = server.request_handlers[types.CallToolRequest]

    result = await handler(request)

    assert isinstance(result, types.ServerResult)
    assert isinstance(result.root, types.CallToolResult)
    assert result.root.isError is False
    assert result.root.structuredContent == {"ok": True}
    assert result.root.content == []
