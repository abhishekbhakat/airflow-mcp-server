"""Tests for HierarchicalToolManager."""

from unittest.mock import Mock

import httpx
import pytest
from fastmcp import FastMCP

from airflow_mcp_server.hierarchical_manager import HierarchicalToolManager


@pytest.fixture
def mock_client():
    """Create mock HTTP client."""
    client = Mock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def mock_mcp():
    """Create mock FastMCP instance."""
    mcp = Mock(spec=FastMCP)
    mcp.tool = Mock()
    return mcp


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI spec for testing."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Airflow API", "version": "1.0.0"},
        "paths": {
            "/api/v1/dags": {
                "get": {"operationId": "get_dags", "summary": "Get all DAGs", "tags": ["DAGs"], "responses": {"200": {"description": "Success"}}},
                "post": {"operationId": "create_dag", "summary": "Create a DAG", "tags": ["DAGs"], "responses": {"201": {"description": "Created"}}},
            },
            "/api/v1/connections": {"get": {"operationId": "get_connections", "summary": "Get connections", "tags": ["Connections"], "responses": {"200": {"description": "Success"}}}},
        },
    }


def test_hierarchical_manager_init(mock_mcp, sample_openapi_spec, mock_client):
    """Test HierarchicalToolManager initialization."""
    manager = HierarchicalToolManager(mcp=mock_mcp, openapi_spec=sample_openapi_spec, client=mock_client, allowed_methods={"GET", "POST"})

    assert manager.mcp == mock_mcp
    assert manager.openapi_spec == sample_openapi_spec
    assert manager.client == mock_client
    assert manager.allowed_methods == {"GET", "POST"}
    assert manager.current_mode == "categories"
    assert isinstance(manager.current_tools, set)


def test_hierarchical_manager_default_methods(mock_mcp, sample_openapi_spec, mock_client):
    """Test HierarchicalToolManager with default allowed methods."""
    manager = HierarchicalToolManager(mcp=mock_mcp, openapi_spec=sample_openapi_spec, client=mock_client)

    # Should default to all methods
    assert manager.allowed_methods == {"GET", "POST", "PUT", "DELETE", "PATCH"}


def test_hierarchical_manager_safe_mode(mock_mcp, sample_openapi_spec, mock_client):
    """Test HierarchicalToolManager in safe mode (GET only)."""
    manager = HierarchicalToolManager(mcp=mock_mcp, openapi_spec=sample_openapi_spec, client=mock_client, allowed_methods={"GET"})

    assert manager.allowed_methods == {"GET"}


def test_persistent_tools_constant():
    """Test that persistent tools are defined correctly."""
    expected_tools = {"browse_categories", "select_category", "get_current_category"}
    assert HierarchicalToolManager.PERSISTENT_TOOLS == expected_tools


def test_hierarchical_manager_attributes(mock_mcp, sample_openapi_spec, mock_client):
    """Test that all required attributes are set."""
    manager = HierarchicalToolManager(mcp=mock_mcp, openapi_spec=sample_openapi_spec, client=mock_client)

    # Check all required attributes exist
    assert hasattr(manager, "mcp")
    assert hasattr(manager, "openapi_spec")
    assert hasattr(manager, "client")
    assert hasattr(manager, "allowed_methods")
    assert hasattr(manager, "current_mode")
    assert hasattr(manager, "current_tools")
    assert hasattr(manager, "category_tool_instances")

    # Check initial values
    assert manager.current_mode == "categories"
    assert isinstance(manager.current_tools, set)
    assert isinstance(manager.category_tool_instances, dict)
