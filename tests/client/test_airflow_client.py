import logging
from unittest.mock import patch

import pytest
from openapi_core import OpenAPI

from airflow_mcp_server.client.airflow_client import AirflowClient

logging.basicConfig(level=logging.DEBUG)


def mock_openapi_response(*args, **kwargs):
    class MockResponse:
        def __init__(self):
            self.status_code = 200

        def json(self):
            return {"openapi": "3.0.0", "info": {"title": "Airflow API", "version": "1.0.0"}, "paths": {}}

    return MockResponse()


@pytest.fixture
def client():
    with patch("airflow_mcp_server.client.airflow_client.requests.get", side_effect=mock_openapi_response):
        return AirflowClient(
            base_url="http://localhost:8080/api/v1",
            auth_token="test-token",
        )


def test_init_client_initialization(client):
    assert isinstance(client.spec, OpenAPI)
    assert client.base_url == "http://localhost:8080/api/v1"
    assert client.headers["Authorization"] == "Bearer test-token"


def test_init_client_missing_auth():
    with pytest.raises(ValueError, match="auth_token"):
        AirflowClient(
            base_url="http://localhost:8080/api/v1",
            auth_token=None,
        )
