"""Test configuration and shared fixtures."""

import pytest


@pytest.fixture
def mock_spec_file():
    """Mock OpenAPI spec file for testing."""
    mock_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Airflow API", "version": "1.0.0"},
        "paths": {
            "/api/v1/dags": {
                "get": {
                    "operationId": "get_dags",
                    "responses": {
                        "200": {
                            "description": "List of DAGs",
                            "content": {
                                "application/json": {"schema": {"type": "object", "properties": {"dags": {"type": "array", "items": {"type": "object", "properties": {"dag_id": {"type": "string"}}}}}}}
                            },
                        }
                    },
                }
            },
            "/api/v1/dags/{dag_id}": {
                "get": {
                    "operationId": "get_dag",
                    "parameters": [{"name": "dag_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Successful response", "content": {"application/json": {"schema": {"type": "object", "properties": {"dag_id": {"type": "string"}}}}}}},
                },
                "post": {
                    "operationId": "post_dag_run",
                    "parameters": [{"name": "dag_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "conf": {"type": "object"},
                                        "dag_run_id": {"type": "string"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {"application/json": {"schema": {"type": "object", "properties": {"dag_run_id": {"type": "string"}, "state": {"type": "string"}}}}},
                        }
                    },
                },
            },
        },
    }
    return mock_spec
