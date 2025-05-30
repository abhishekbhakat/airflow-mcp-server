"""Tests for server modules."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
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
async def test_safe_server_initialization(mock_config, mock_openapi_response):
    """Test safe server initialization."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = mock_openapi_response
        mock_client.get.return_value = mock_response

        with patch("airflow_mcp_server.server_safe.FastMCP") as mock_fastmcp:
            with patch("airflow_mcp_server.server_safe.HierarchicalToolManager") as mock_manager:
                with patch("airflow_mcp_server.server_safe.add_airflow_resources") as mock_resources:
                    with patch("airflow_mcp_server.server_safe.add_airflow_prompts") as mock_prompts:
                        mock_mcp_instance = Mock()
                        mock_fastmcp.return_value = mock_mcp_instance
                        mock_mcp_instance.run_async = AsyncMock()

                        # This should not raise an exception
                        await server_safe.serve(mock_config)

                        # Verify client was created with correct parameters
                        mock_client_class.assert_called_once_with(base_url="http://localhost:8080", headers={"Authorization": "Bearer test-token"}, timeout=30.0)

                        # Verify OpenAPI spec was fetched
                        mock_client.get.assert_called_once_with("/openapi.json")

                        # Verify FastMCP was created
                        mock_fastmcp.assert_called_once_with("Airflow MCP Server (Safe Mode)")

                        # Verify HierarchicalToolManager was created with safe mode
                        mock_manager.assert_called_once()
                        call_args = mock_manager.call_args
                        assert call_args[1]["allowed_methods"] == {"GET"}

                        # Verify resources and prompts were added
                        mock_resources.assert_called_once_with(mock_mcp_instance, mock_config, mode="safe")
                        mock_prompts.assert_called_once_with(mock_mcp_instance, mode="safe")


@pytest.mark.asyncio
async def test_unsafe_server_initialization(mock_config, mock_openapi_response):
    """Test unsafe server initialization."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = mock_openapi_response
        mock_client.get.return_value = mock_response

        with patch("airflow_mcp_server.server_unsafe.FastMCP") as mock_fastmcp:
            with patch("airflow_mcp_server.server_unsafe.HierarchicalToolManager") as mock_manager:
                with patch("airflow_mcp_server.server_unsafe.add_airflow_resources") as mock_resources:
                    with patch("airflow_mcp_server.server_unsafe.add_airflow_prompts") as mock_prompts:
                        mock_mcp_instance = Mock()
                        mock_fastmcp.return_value = mock_mcp_instance
                        mock_mcp_instance.run_async = AsyncMock()

                        # This should not raise an exception
                        await server_unsafe.serve(mock_config)

                        # Verify FastMCP was created
                        mock_fastmcp.assert_called_once_with("Airflow MCP Server (Unsafe Mode)")

                        # Verify HierarchicalToolManager was created with all methods
                        mock_manager.assert_called_once()
                        call_args = mock_manager.call_args
                        assert call_args[1]["allowed_methods"] == {"GET", "POST", "PUT", "DELETE", "PATCH"}

                        # Verify resources and prompts were added
                        mock_resources.assert_called_once_with(mock_mcp_instance, mock_config, mode="unsafe")
                        mock_prompts.assert_called_once_with(mock_mcp_instance, mode="unsafe")


@pytest.mark.asyncio
async def test_server_openapi_fetch_error(mock_config):
    """Test server handling of OpenAPI fetch error."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock HTTP error
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        with pytest.raises(httpx.HTTPError):
            await server_safe.serve(mock_config)

        # Verify client was closed on error
        mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_server_run_error(mock_config, mock_openapi_response):
    """Test server handling of run error."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock successful OpenAPI fetch
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = mock_openapi_response
        mock_client.get.return_value = mock_response

        with patch("airflow_mcp_server.server_safe.FastMCP") as mock_fastmcp:
            with patch("airflow_mcp_server.server_safe.HierarchicalToolManager"):
                with patch("airflow_mcp_server.server_safe.add_airflow_resources"):
                    with patch("airflow_mcp_server.server_safe.add_airflow_prompts"):
                        mock_mcp_instance = Mock()
                        mock_fastmcp.return_value = mock_mcp_instance
                        mock_mcp_instance.run_async = AsyncMock(side_effect=RuntimeError("Server error"))

                        with pytest.raises(RuntimeError):
                            await server_safe.serve(mock_config)

                        # Verify client was closed on error
                        mock_client.aclose.assert_called_once()
