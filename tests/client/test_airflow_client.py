import asyncio
import logging
from unittest.mock import patch

import pytest
from openapi_core import OpenAPI

from airflow_mcp_server.client.airflow_client import AirflowClient

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.asyncio
async def test_async_multiple_clients_concurrent():
    """Test initializing two AirflowClients concurrently to verify async power."""

    async def mock_get(self, url, *args, **kwargs):
        class MockResponse:
            def __init__(self):
                self.status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"openapi": "3.1.0", "info": {"title": "Airflow API", "version": "2.0.0"}, "paths": {}}

        return MockResponse()

    with patch("httpx.AsyncClient.get", new=mock_get):

        async def create_and_check():
            async with AirflowClient(base_url="http://localhost:8080", auth_token="token") as client:
                assert client.base_url == "http://localhost:8080"
                assert client.headers["Authorization"] == "Bearer token"
                assert isinstance(client.spec, OpenAPI)

        # Run two clients concurrently
        await asyncio.gather(create_and_check(), create_and_check())


@pytest.mark.asyncio
async def test_async_client_initialization():
    async def mock_get(self, url, *args, **kwargs):
        class MockResponse:
            def __init__(self):
                self.status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"openapi": "3.1.0", "info": {"title": "Airflow API", "version": "2.0.0"}, "paths": {}}

        return MockResponse()

    with patch("httpx.AsyncClient.get", new=mock_get):
        async with AirflowClient(base_url="http://localhost:8080", auth_token="test-token") as client:
            assert client.base_url == "http://localhost:8080"
            assert client.headers["Authorization"] == "Bearer test-token"
            assert isinstance(client.spec, OpenAPI)


def test_init_client_missing_auth():
    with pytest.raises(ValueError, match="auth_token"):
        AirflowClient(
            base_url="http://localhost:8080",
            auth_token=None,
        )
