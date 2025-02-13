import logging
from importlib import resources
from pathlib import Path
from typing import Any

import aiohttp
import pytest
import yaml
from aioresponses import aioresponses
from airflow_mcp_server.client.airflow_client import AirflowClient
from openapi_core import OpenAPI

logging.basicConfig(level=logging.DEBUG)


def create_valid_spec(paths: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"openapi": "3.0.0", "info": {"title": "Airflow API", "version": "1.0.0"}, "paths": paths or {}}


@pytest.fixture
def spec_file() -> dict[str, Any]:
    with resources.files("tests.client").joinpath("v1.yaml").open("r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def client(spec_file: dict[str, Any]) -> AirflowClient:
    return AirflowClient(
        spec_path=spec_file,
        base_url="http://localhost:8080/api/v1",
        auth_token="test-token",
    )


def test_init_client_initialization(client: AirflowClient) -> None:
    assert isinstance(client.spec, OpenAPI)
    assert client.base_url == "http://localhost:8080/api/v1"
    assert client.headers["Authorization"] == "Bearer test-token"


def test_init_load_spec_from_bytes() -> None:
    spec_bytes = yaml.dump(create_valid_spec()).encode()
    client = AirflowClient(spec_path=spec_bytes, base_url="http://test", auth_token="test")
    assert client.raw_spec is not None


def test_init_load_spec_from_path(tmp_path: Path) -> None:
    spec_file = tmp_path / "test_spec.yaml"
    spec_file.write_text(yaml.dump(create_valid_spec()))
    client = AirflowClient(spec_path=spec_file, base_url="http://test", auth_token="test")
    assert client.raw_spec is not None


def test_init_invalid_spec() -> None:
    with pytest.raises(ValueError):
        AirflowClient(spec_path={"invalid": "spec"}, base_url="http://test", auth_token="test")


def test_init_missing_paths_in_spec() -> None:
    with pytest.raises(ValueError):
        AirflowClient(spec_path={"openapi": "3.0.0"}, base_url="http://test", auth_token="test")


def test_ops_get_operation(client: AirflowClient) -> None:
    path, method, operation = client._get_operation("get_dags")
    assert path == "/dags"
    assert method == "get"
    assert operation.operation_id == "get_dags"

    path, method, operation = client._get_operation("get_dag")
    assert path == "/dags/{dag_id}"
    assert method == "get"
    assert operation.operation_id == "get_dag"


def test_ops_nonexistent_operation(client: AirflowClient) -> None:
    with pytest.raises(ValueError, match="Operation nonexistent not found in spec"):
        client._get_operation("nonexistent")


def test_ops_case_sensitive_operation(client: AirflowClient) -> None:
    with pytest.raises(ValueError):
        client._get_operation("GET_DAGS")


@pytest.mark.asyncio
async def test_exec_without_context(spec_file: dict[str, Any]) -> None:
    client = AirflowClient(
        spec_path=spec_file,
        base_url="http://test",
        auth_token="test",
    )
    with pytest.raises(RuntimeError, match="Client not in async context"):
        await client.execute("get_dags")


@pytest.mark.asyncio
async def test_exec_get_dags(client: AirflowClient) -> None:
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
async def test_exec_get_dag(client: AirflowClient) -> None:
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
async def test_exec_invalid_params(client: AirflowClient) -> None:
    with pytest.raises(ValueError):
        async with client:
            # Test with missing required parameter
            await client.execute("get_dag", path_params={})

    with pytest.raises(ValueError):
        async with client:
            # Test with invalid parameter name
            await client.execute("get_dag", path_params={"invalid": "value"})


@pytest.mark.asyncio
async def test_exec_timeout(client: AirflowClient) -> None:
    with aioresponses() as mock:
        mock.get("http://localhost:8080/api/v1/dags", exception=aiohttp.ClientError("Timeout"))
        async with client:
            with pytest.raises(aiohttp.ClientError):
                await client.execute("get_dags")


@pytest.mark.asyncio
async def test_exec_error_response(client: AirflowClient) -> None:
    with aioresponses() as mock:
        async with client:
            mock.get(
                "http://localhost:8080/api/v1/dags",
                status=403,
                body="Forbidden",
            )
            with pytest.raises(aiohttp.ClientResponseError):
                await client.execute("get_dags")


@pytest.mark.asyncio
async def test_exec_session_management(client: AirflowClient) -> None:
    async with client:
        with aioresponses() as mock:
            mock.get(
                "http://localhost:8080/api/v1/dags",
                status=200,
                payload={"dags": []},
            )
            await client.execute("get_dags")

    with pytest.raises(RuntimeError):
        await client.execute("get_dags")
