import logging
from importlib import resources

import aiohttp
import pytest
from aioresponses import aioresponses
from airflow_mcp_server.client import AirflowClient
from openapi_core import OpenAPI

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


@pytest.fixture
def spec_file():
    """Get content of the v1.yaml spec file."""
    with resources.files("tests.client").joinpath("v1.yaml").open("rb") as f:
        return f.read()


@pytest.fixture
def client(spec_file):
    """Create test client with the actual spec."""
    return AirflowClient(
        spec_path=spec_file,
        base_url="http://localhost:8080/api/v1",
        auth_token="test-token",
    )


def test_client_initialization(client):
    """Test client initialization and spec loading."""
    assert isinstance(client.spec, OpenAPI)
    assert client.base_url == "http://localhost:8080/api/v1"
    assert client.headers["Authorization"] == "Bearer test-token"


def test_get_operation(client):
    """Test operation lookup from spec."""
    # Test get_dags operation
    path, method, operation = client._get_operation("get_dags")
    assert path == "/dags"
    assert method == "get"
    assert operation.operation_id == "get_dags"

    # Test get_dag operation
    path, method, operation = client._get_operation("get_dag")
    assert path == "/dags/{dag_id}"
    assert method == "get"
    assert operation.operation_id == "get_dag"


# Note: asyncio_mode is configured in pyproject.toml
@pytest.mark.asyncio
async def test_execute_without_context():
    """Test error when executing outside async context."""
    with resources.files("tests.client").joinpath("v1.yaml").open("rb") as f:
        client = AirflowClient(
            spec_path=f,
            base_url="http://test",
            auth_token="test",
        )
    with pytest.raises(RuntimeError, match="Client not in async context"):
        await client.execute("get_dags")


@pytest.mark.asyncio
async def test_execute_get_dags(client):
    """Test DAG list retrieval."""
    expected_response = {
        "dags": [
            {
                "dag_id": "test_dag",
                "is_active": True,
                "is_paused": False,
            }
        ],
        "total_entries": 1,
    }

    with aioresponses() as mock:
        async with client:
            mock.get(
                "http://localhost:8080/api/v1/dags?limit=100",
                status=200,
                payload=expected_response,
            )
            response = await client.execute("get_dags", query_params={"limit": 100})
            assert response == expected_response


@pytest.mark.asyncio
async def test_execute_get_dag(client):
    """Test single DAG retrieval with path parameters."""
    expected_response = {
        "dag_id": "test_dag",
        "is_active": True,
        "is_paused": False,
    }

    with aioresponses() as mock:
        async with client:
            mock.get(
                "http://localhost:8080/api/v1/dags/test_dag",
                status=200,
                payload=expected_response,
            )
            response = await client.execute(
                "get_dag",
                path_params={"dag_id": "test_dag"},
            )
            assert response == expected_response


@pytest.mark.asyncio
async def test_execute_error_response(client):
    """Test error handling for failed requests."""
    with aioresponses() as mock:
        async with client:
            mock.get(
                "http://localhost:8080/api/v1/dags",
                status=403,
                body="Forbidden",
            )
            with pytest.raises(aiohttp.ClientError):
                await client.execute("get_dags")


@pytest.mark.asyncio
async def test_session_management(client):
    """Test proper session creation and cleanup."""
    assert client._session is None

    async with client:
        assert client._session is not None
        assert not client._session.closed

    assert client._session is None
