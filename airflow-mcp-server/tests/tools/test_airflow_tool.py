"""Tests for AirflowTool."""

import pytest
from airflow_mcp_server.client.airflow_client import AirflowClient
from airflow_mcp_server.parser.operation_parser import OperationDetails
from airflow_mcp_server.tools.airflow_tool import AirflowTool
from pydantic import ValidationError

from tests.tools.test_models import TestRequestModel, TestResponseModel


@pytest.fixture
def mock_client(mocker):
    """Create mock Airflow client."""
    client = mocker.Mock(spec=AirflowClient)
    client.execute = mocker.AsyncMock()
    return client


@pytest.fixture
def operation_details():
    """Create test operation details."""
    return OperationDetails(
        operation_id="test_operation",
        path="/test/{id}",
        method="POST",
        parameters={
            "path": {
                "id": {"type": int, "required": True},
            },
            "query": {
                "filter": {"type": str, "required": False},
            },
        },
        request_body=TestRequestModel,
        response_model=TestResponseModel,
    )


@pytest.fixture
def airflow_tool(mock_client, operation_details):
    """Create AirflowTool instance for testing."""
    return AirflowTool(operation_details, mock_client)


@pytest.mark.asyncio
async def test_successful_execution(airflow_tool, mock_client):
    """Test successful operation execution with valid parameters."""
    # Setup mock response
    mock_client.execute.return_value = {"item_id": 1, "result": "success"}

    # Execute operation
    result = await airflow_tool.run(
        path_params={"id": 123},
        query_params={"filter": "test"},
        body={"name": "test", "value": 42},
    )

    # Verify response
    assert result == {"item_id": 1, "result": "success"}
    mock_client.execute.assert_called_once_with(
        operation_id="test_operation",
        path_params={"id": 123},
        query_params={"filter": "test"},
        body={"name": "test", "value": 42},
    )


@pytest.mark.asyncio
async def test_invalid_path_parameter(airflow_tool):
    """Test validation error for invalid path parameter type."""
    with pytest.raises(ValidationError):
        await airflow_tool.run(
            path_params={"id": "not_an_integer"},
            body={"name": "test", "value": 42},
        )


@pytest.mark.asyncio
async def test_invalid_request_body(airflow_tool):
    """Test validation error for invalid request body."""
    with pytest.raises(ValidationError):
        await airflow_tool.run(
            path_params={"id": 123},
            body={"name": "test", "value": "not_an_integer"},
        )


@pytest.mark.asyncio
async def test_invalid_response_format(airflow_tool, mock_client):
    """Test error handling for invalid response format."""
    # Setup mock response with invalid format
    mock_client.execute.return_value = {"invalid": "response"}

    with pytest.raises(RuntimeError):
        await airflow_tool.run(
            path_params={"id": 123},
            body={"name": "test", "value": 42},
        )


@pytest.mark.asyncio
async def test_client_error(airflow_tool, mock_client):
    """Test error handling for client execution failure."""
    # Setup mock to raise exception
    mock_client.execute.side_effect = RuntimeError("API Error")

    with pytest.raises(RuntimeError):
        await airflow_tool.run(
            path_params={"id": 123},
            body={"name": "test", "value": 42},
        )
