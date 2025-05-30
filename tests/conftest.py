"""Test configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI spec for testing across multiple test files."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Airflow API", "version": "1.0.0"},
        "paths": {
            "/api/v1/dags": {
                "get": {
                    "operationId": "get_dags",
                    "summary": "Get all DAGs",
                    "tags": ["DAGs"],
                    "responses": {
                        "200": {
                            "description": "List of DAGs",
                            "content": {
                                "application/json": {"schema": {"type": "object", "properties": {"dags": {"type": "array", "items": {"type": "object", "properties": {"dag_id": {"type": "string"}}}}}}}
                            },
                        }
                    },
                },
                "post": {"operationId": "create_dag", "summary": "Create a DAG", "tags": ["DAGs"], "responses": {"201": {"description": "Created"}}},
            },
            "/api/v1/connections": {"get": {"operationId": "get_connections", "summary": "Get connections", "tags": ["Connections"], "responses": {"200": {"description": "Success"}}}},
        },
    }
