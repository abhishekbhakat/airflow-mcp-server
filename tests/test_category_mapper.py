"""Tests for category mapper utilities."""

import pytest

from airflow_mcp_server.utils.category_mapper import extract_categories_from_openapi, filter_routes_by_methods, get_category_info, get_category_tools_info, get_tool_name_from_route


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI spec for testing."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/api/v1/dags": {"get": {"operationId": "get_dags", "summary": "Get all DAGs", "tags": ["DAGs"]}, "post": {"operationId": "create_dag", "summary": "Create a DAG", "tags": ["DAGs"]}},
            "/api/v1/connections": {"get": {"operationId": "get_connections", "summary": "Get connections", "tags": ["Connections"]}},
            "/api/v1/health": {
                "get": {
                    "operationId": "health_check",
                    "summary": "Health check",
                    # No tags - should go to "Uncategorized"
                }
            },
        },
    }


def test_extract_categories_from_openapi(sample_openapi_spec):
    """Test extracting categories from OpenAPI spec."""
    categories = extract_categories_from_openapi(sample_openapi_spec)

    assert "DAGs" in categories
    assert "Connections" in categories
    assert "Uncategorized" in categories

    # Check DAGs category has 2 operations
    assert len(categories["DAGs"]) == 2
    assert len(categories["Connections"]) == 1
    assert len(categories["Uncategorized"]) == 1


def test_extract_categories_empty_spec():
    """Test extracting categories from empty spec."""
    categories = extract_categories_from_openapi({})
    assert categories == {}


def test_extract_categories_no_paths():
    """Test extracting categories from spec with no paths."""
    spec = {"openapi": "3.0.0", "info": {"title": "Test"}}
    categories = extract_categories_from_openapi(spec)
    assert categories == {}


def test_filter_routes_by_methods():
    """Test filtering routes by allowed methods."""
    routes = [{"method": "GET", "operation_id": "get_dags"}, {"method": "POST", "operation_id": "create_dag"}, {"method": "DELETE", "operation_id": "delete_dag"}]

    # Filter to only GET methods
    filtered = filter_routes_by_methods(routes, {"GET"})
    assert len(filtered) == 1
    assert filtered[0]["operation_id"] == "get_dags"

    # Filter to GET and POST
    filtered = filter_routes_by_methods(routes, {"GET", "POST"})
    assert len(filtered) == 2


def test_get_category_info():
    """Test getting formatted category information."""
    categories = {"DAGs": [{"method": "GET"}, {"method": "POST"}], "Connections": [{"method": "GET"}]}

    info = get_category_info(categories)

    assert "Available Airflow Categories:" in info
    assert "DAGs: 2 tools" in info
    assert "Connections: 1 tools" in info
    assert "Total: 2 categories, 3 tools" in info
    assert 'select_category("Category Name")' in info


def test_get_category_info_empty():
    """Test getting category info for empty categories."""
    info = get_category_info({})
    assert info == "No categories found."


def test_get_category_tools_info():
    """Test getting formatted tools information for a category."""
    routes = [
        {"method": "GET", "operation_id": "get_dags", "summary": "Get all DAGs", "description": "Retrieve all DAGs"},
        {"method": "POST", "operation_id": "create_dag", "summary": "Create a new DAG", "description": ""},
    ]

    info = get_category_tools_info("DAGs", routes)

    assert "DAGs Tools (2 available):" in info
    assert "GET Operations:" in info
    assert "POST Operations:" in info
    assert "get_dags: Get all DAGs" in info
    assert "create_dag: Create a new DAG" in info
    assert "back_to_categories()" in info


def test_get_tool_name_from_route():
    """Test generating tool names from route information."""
    # Test with operation_id
    route = {"operation_id": "get_dags", "path": "/api/v1/dags", "method": "GET"}
    assert get_tool_name_from_route(route) == "get_dags"

    # Test without operation_id (fallback)
    route = {"path": "/api/v1/dags/{dag_id}", "method": "POST"}
    expected = "post_api_v1_dags_dag_id"
    assert get_tool_name_from_route(route) == expected


def test_get_tool_name_from_route_empty():
    """Test generating tool name with minimal route info."""
    route = {"path": "/", "method": "GET"}
    assert get_tool_name_from_route(route) == "get_"
