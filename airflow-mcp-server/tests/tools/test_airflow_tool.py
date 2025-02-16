"""Tests for AirflowTool."""

import pytest
from airflow_mcp_server.client.airflow_client import AirflowClient
from airflow_mcp_server.parser.operation_parser import OperationDetails
from airflow_mcp_server.tools.airflow_tool import AirflowTool
from pydantic import ValidationError

from tests.tools.test_models import TestRequestModel


@pytest.fixture
def mock_client(mocker):
    """Create mock Airflow client."""
    client = mocker.Mock(spec=AirflowClient)
    client.execute = mocker.AsyncMock()
    return client


@pytest.fixture
def operation_details():
    """Create test operation details."""
    model = TestRequestModel
    # Add parameter mapping to model config
    model.model_config["parameter_mapping"] = {
        "path": ["path_id"],
        "query": ["query_filter"],
        "body": ["body_name", "body_value"],
    }

    return OperationDetails(
        operation_id="test_operation",
        path="/test/{path_id}",
        method="POST",
        parameters={
            "path": {
                "path_id": {"type": int, "required": True},
            },
            "query": {
                "query_filter": {"type": str, "required": False},
            },
        },
        input_model=model,
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

    # Execute operation with unified body
    result = await airflow_tool.run(
        body={
            "path_id": 123,
            "query_filter": "test",
            "body_name": "test",
            "body_value": 42,
        }
    )

    # Verify response
    assert result == {"item_id": 1, "result": "success"}
    mock_client.execute.assert_called_once_with(
        operation_id="test_operation",
        path_params={"path_id": 123},
        query_params={"query_filter": "test"},
        body={"body_name": "test", "body_value": 42},
    )


@pytest.mark.asyncio
async def test_invalid_path_parameter(airflow_tool):
    """Test validation error for invalid path parameter type."""
    with pytest.raises(ValidationError):
        await airflow_tool.run(
            body={
                "path_id": "not_an_integer",  # Invalid type
                "body_name": "test",
                "body_value": 42,
            }
        )


@pytest.mark.asyncio
async def test_invalid_request_body(airflow_tool):
    """Test validation error for invalid request body."""
    with pytest.raises(ValidationError):
        await airflow_tool.run(
            body={
                "path_id": 123,
                "body_name": "test",
                "body_value": "not_an_integer",  # Invalid type
            }
        )


@pytest.mark.asyncio
async def test_invalid_response_format(airflow_tool, mock_client):
    """Test error handling for invalid response format."""
    # Setup mock response
    mock_client.execute.return_value = {"invalid": "response"}

    # Should not raise any validation error
    result = await airflow_tool.run(
        body={
            "path_id": 123,
            "body_name": "test",
            "body_value": 42,
        }
    )
    assert result == {"invalid": "response"}


@pytest.mark.asyncio
async def test_client_error(airflow_tool, mock_client):
    """Test error handling for client execution failure."""
    # Setup mock to raise exception
    mock_client.execute.side_effect = RuntimeError("API Error")

    with pytest.raises(RuntimeError):
        await airflow_tool.run(
            body={
                "path_id": 123,
                "body_name": "test",
                "body_value": 42,
            }
        )
