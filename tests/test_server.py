"""Tests for server modules."""

from typing import Any
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest

from airflow_mcp_server import server_safe, server_unsafe
from airflow_mcp_server.config import AirflowConfig


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return AirflowConfig(base_url="http://localhost:8080", auth_token="test-token")


@pytest.fixture
def mock_openapi_response():
    """Mock OpenAPI response."""
    return {"openapi": "3.0.0", "info": {"title": "Airflow API", "version": "1.0.0"}, "paths": {"/api/v1/dags": {"get": {"operationId": "get_dags", "summary": "Get all DAGs", "tags": ["DAGs"]}}}}


@pytest.mark.asyncio
async def test_safe_server_delegates_to_runtime(mock_config):
    runtime_mock = AsyncMock()
    with patch("airflow_mcp_server.server_safe._serve_airflow", runtime_mock):
        await server_safe.serve(mock_config, static_tools=True, transport="stdio", resources_dir="/tmp/resources")

    runtime_mock.assert_awaited_once()
    await_args = runtime_mock.await_args
    assert await_args is not None
    kwargs = await_args.kwargs
    assert kwargs["allowed_methods"] == {"GET"}
    assert kwargs["static_tools"] is True
    assert kwargs["resources_dir"] == "/tmp/resources"


@pytest.mark.asyncio
async def test_unsafe_server_delegates_to_runtime(mock_config):
    runtime_mock = AsyncMock()
    with patch("airflow_mcp_server.server_unsafe._serve_airflow", runtime_mock):
        await server_unsafe.serve(mock_config, static_tools=False, transport="streamable-http")

    runtime_mock.assert_awaited_once()
    await_args = runtime_mock.await_args
    assert await_args is not None
    kwargs = await_args.kwargs
    assert kwargs["allowed_methods"] == {"GET", "POST", "PUT", "DELETE", "PATCH"}
    assert kwargs["transport"] == "streamable-http"


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, response: Any):
        self._response = response
        self.closed = False
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def get(self, path):
        return self._response

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_serve_airflow_static_tools(monkeypatch, mock_config, mock_openapi_response):
    fake_response = _FakeResponse(mock_openapi_response)
    fake_session = _FakeSession(fake_response)

    monkeypatch.setattr("airflow_mcp_server.server_safe.aiohttp.ClientSession", lambda **_: fake_session)

    toolset_instance = Mock()
    with patch("airflow_mcp_server.server_safe.AirflowOpenAPIToolset", return_value=toolset_instance) as toolset_cls:
        with patch("airflow_mcp_server.server_safe._register_static_tools") as register_static:
            with patch("airflow_mcp_server.server_safe.HierarchicalToolManager") as manager_cls:
                with patch("airflow_mcp_server.server_safe.register_resources") as register_resources:
                    run_stdio = AsyncMock()
                    with patch("airflow_mcp_server.server_safe._run_stdio", run_stdio):
                        await server_safe._serve_airflow(
                            config=mock_config,
                            allowed_methods={"GET"},
                            mode_label="Safe Mode",
                            static_tools=True,
                            resources_dir=None,
                            transport="stdio",
                            transport_kwargs={},
                        )

    toolset_cls.assert_called_once_with(mock_openapi_response, allow_mutations=False, session=fake_session)
    register_static.assert_called_once()
    manager_cls.assert_not_called()
    register_resources.assert_called_once()
    run_stdio.assert_awaited_once()
    assert fake_session.closed is True


@pytest.mark.asyncio
async def test_serve_airflow_hierarchical_http(monkeypatch, mock_config, mock_openapi_response):
    fake_response = _FakeResponse(mock_openapi_response)
    fake_session = _FakeSession(fake_response)

    monkeypatch.setattr("airflow_mcp_server.server_safe.aiohttp.ClientSession", lambda **_: fake_session)

    toolset_instance = Mock()
    with patch("airflow_mcp_server.server_safe.AirflowOpenAPIToolset", return_value=toolset_instance) as toolset_cls:
        register_static = patch("airflow_mcp_server.server_safe._register_static_tools").start()
        register_resources = patch("airflow_mcp_server.server_safe.register_resources").start()
        manager_cls = patch("airflow_mcp_server.server_safe.HierarchicalToolManager").start()
        run_http = AsyncMock()
        patch("airflow_mcp_server.server_safe._run_streamable_http", run_http).start()
        try:
            await server_safe._serve_airflow(
                config=mock_config,
                allowed_methods={"GET", "POST"},
                mode_label="Unsafe Mode",
                static_tools=False,
                resources_dir="/tmp/resources",
                transport="streamable-http",
                transport_kwargs={"host": "127.0.0.1", "port": 4000},
            )
        finally:
            patch.stopall()

    toolset_cls.assert_called_once_with(mock_openapi_response, allow_mutations=True, session=fake_session)
    register_static.assert_not_called()
    manager_cls.assert_called_once()
    register_resources.assert_called_once()
    run_http.assert_awaited_once_with(ANY, host="127.0.0.1", port=4000)
    assert fake_session.closed is True


@pytest.mark.asyncio
async def test_serve_airflow_fetch_error(monkeypatch, mock_config):
    class FailingResponse:
        async def __aenter__(self):
            raise RuntimeError("boom")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FailingSession(_FakeSession):
        def get(self, path):
            return FailingResponse()

    fake_session = FailingSession(None)
    monkeypatch.setattr("airflow_mcp_server.server_safe.aiohttp.ClientSession", lambda **_: fake_session)

    with pytest.raises(RuntimeError):
        await server_safe._serve_airflow(
            config=mock_config,
            allowed_methods={"GET"},
            mode_label="Safe Mode",
            static_tools=True,
            resources_dir=None,
            transport="stdio",
            transport_kwargs={},
        )

    assert fake_session.closed is True


@pytest.mark.asyncio
async def test_serve_airflow_requires_valid_config():
    config_no_url = AirflowConfig.__new__(AirflowConfig)
    config_no_url.base_url = None
    config_no_url.auth_token = "token"

    with pytest.raises(ValueError, match="base_url is required"):
        await server_safe._serve_airflow(
            config=config_no_url,
            allowed_methods={"GET"},
            mode_label="Safe Mode",
            static_tools=True,
            resources_dir=None,
            transport="stdio",
            transport_kwargs={},
        )

    config_no_token = AirflowConfig.__new__(AirflowConfig)
    config_no_token.base_url = "http://localhost"
    config_no_token.auth_token = None

    with pytest.raises(ValueError, match="auth_token is required"):
        await server_safe._serve_airflow(
            config=config_no_token,
            allowed_methods={"GET"},
            mode_label="Safe Mode",
            static_tools=True,
            resources_dir=None,
            transport="stdio",
            transport_kwargs={},
        )
