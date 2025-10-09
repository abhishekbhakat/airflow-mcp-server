"""Tests for HierarchicalToolManager."""

from types import SimpleNamespace

import pytest
from mcp import types

from airflow_mcp_server.hierarchical_manager import HierarchicalToolManager


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI spec for testing."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Airflow API", "version": "1.0.0"},
        "paths": {
            "/api/v1/dags": {
                "get": {
                    "operationId": "get_dags",
                    "summary": "Get all DAGs",
                    "tags": ["DAGs"],
                    "responses": {"200": {"description": "Success"}},
                }
            },
            "/api/v1/connections": {
                "get": {
                    "operationId": "get_connections",
                    "summary": "Get connections",
                    "tags": ["Connections"],
                    "responses": {"200": {"description": "Success"}},
                }
            },
        },
    }


class FakeSession:
    def __init__(self) -> None:
        self.notifications = 0

    async def send_tool_list_changed(self) -> None:
        self.notifications += 1


class FakeServer:
    def __init__(self) -> None:
        self.list_handlers = []
        self.call_handlers = []
        self._request_context = SimpleNamespace(session=FakeSession())

    def list_tools(self):
        def decorator(func):
            self.list_handlers.append(func)
            return func

        return decorator

    def call_tool(self):
        def decorator(func):
            self.call_handlers.append(func)
            return func

        return decorator

    @property
    def request_context(self):
        return self._request_context


class FakeToolset:
    def __init__(self) -> None:
        self.tool = types.Tool(
            name="get_dags",
            description="Fetch DAGs",
            inputSchema={"type": "object"},
            outputSchema=None,
        )
        self.last_call: tuple[str, dict[str, str]] | None = None

    def list_tools(self):
        return [self.tool]

    def get_tool(self, name: str):
        return self.tool, None

    async def call_tool(self, name: str, arguments: dict[str, str]):
        self.last_call = (name, arguments)
        return [types.TextContent(type="text", text="ok")]


@pytest.mark.asyncio
async def test_hierarchical_manager_navigation(sample_openapi_spec):
    server = FakeServer()
    toolset = FakeToolset()

    HierarchicalToolManager(server, toolset, sample_openapi_spec, {"GET"})

    assert len(server.list_handlers) == 1
    assert len(server.call_handlers) == 1

    list_handler = server.list_handlers[0]
    call_handler = server.call_handlers[0]

    result = await list_handler(None)
    nav_names = {tool.name for tool in result.tools}
    assert {"browse_categories", "select_category", "get_current_category", "back_to_categories"}.issubset(nav_names)

    await call_handler("select_category", {"category": "DAGs"})
    assert server.request_context.session.notifications == 1

    result_after = await list_handler(None)
    tool_names = {tool.name for tool in result_after.tools}
    assert "get_dags" in tool_names

    await call_handler("get_dags", {"foo": "bar"})
    assert toolset.last_call == ("get_dags", {"foo": "bar"})
