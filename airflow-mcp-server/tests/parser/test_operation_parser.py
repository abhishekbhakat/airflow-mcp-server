import logging
from importlib import resources
from typing import Any

import pytest
from airflow_mcp_server.parser.operation_parser import OperationDetails, OperationParser
from pydantic import BaseModel

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
def spec_file():
    """Get content of the v1.yaml spec file."""
    with resources.files("tests.client").joinpath("v1.yaml").open("rb") as f:
        return f.read()


@pytest.fixture
def parser(spec_file) -> OperationParser:
    """Create OperationParser instance."""
    return OperationParser(spec_path=spec_file)


def test_parse_operation_basic(parser: OperationParser) -> None:
    """Test basic operation parsing."""
    operation = parser.parse_operation("get_dags")

    assert isinstance(operation, OperationDetails)
    assert operation.operation_id == "get_dags"
    assert operation.path == "/dags"
    assert operation.method == "get"
    assert isinstance(operation.parameters, dict)


def test_parse_operation_with_path_params(parser: OperationParser) -> None:
    """Test parsing operation with path parameters."""
    operation = parser.parse_operation("get_dag")

    assert operation.path == "/dags/{dag_id}"
    assert isinstance(operation.input_model, type(BaseModel))

    # Verify path parameter field exists
    fields = operation.input_model.__annotations__
    assert "path_dag_id" in fields
    assert isinstance(fields["path_dag_id"], type(str))


def test_parse_operation_with_query_params(parser: OperationParser) -> None:
    """Test parsing operation with query parameters."""
    operation = parser.parse_operation("get_dags")

    # Verify query parameter field exists
    fields = operation.input_model.__annotations__
    assert "query_limit" in fields
    assert isinstance(fields["query_limit"], type(int))


def test_parse_operation_with_body_params(parser: OperationParser) -> None:
    """Test parsing operation with request body."""
    operation = parser.parse_operation("post_dag_run")

    # Verify body fields exist
    fields = operation.input_model.__annotations__
    assert "body_dag_run_id" in fields
    assert isinstance(fields["body_dag_run_id"], type(str))


def test_parse_operation_with_response_model(parser: OperationParser) -> None:
    """Test parsing operation with response model."""
    operation = parser.parse_operation("get_dag")

    assert operation.response_model is not None
    assert issubclass(operation.response_model, BaseModel)

    # Test model fields
    fields = operation.response_model.__annotations__
    assert "dag_id" in fields
    assert "is_paused" in fields


def test_parse_operation_not_found(parser: OperationParser) -> None:
    """Test error handling for non-existent operation."""
    with pytest.raises(ValueError, match="Operation invalid_op not found in spec"):
        parser.parse_operation("invalid_op")


def test_extract_parameters_empty(parser: OperationParser) -> None:
    """Test parameter extraction with no parameters."""
    params = parser.extract_parameters({})

    assert isinstance(params, dict)
    assert "path" in params
    assert "query" in params
    assert "header" in params
    assert all(isinstance(v, dict) for v in params.values())


def test_map_parameter_schema_array(parser: OperationParser) -> None:
    """Test mapping array parameter schema."""
    param: dict[str, Any] = {
        "name": "tags",
        "in": "query",
        "schema": {"type": "array", "items": {"type": "string"}},
    }

    result = parser._map_parameter_schema(param)
    assert isinstance(result["type"], type(list))


def test_map_parameter_schema_nullable(parser: OperationParser) -> None:
    """Test mapping nullable parameter schema."""
    param: dict[str, Any] = {
        "name": "test",
        "in": "query",
        "schema": {"type": "string", "nullable": True},
    }

    result = parser._map_parameter_schema(param)
    assert isinstance(result["type"], type(str))
    assert not result["required"]


def test_create_model_invalid_schema(parser: OperationParser) -> None:
    """Test error handling for invalid schema."""
    with pytest.raises(ValueError, match="Schema must be an object type"):
        parser._create_model("Test", {"type": "string"})


def test_create_model_nested_objects(parser: OperationParser) -> None:
    """Test creating model with nested objects."""
    schema = {
        "type": "object",
        "properties": {"nested": {"type": "object", "properties": {"field": {"type": "string"}}}},
    }

    model = parser._create_model("Test", schema)
    assert issubclass(model, BaseModel)
    fields = model.__annotations__
    assert "nested" in fields
    assert issubclass(fields["nested"], BaseModel)
    nested_fields = fields["nested"].__annotations__
    assert "field" in nested_fields
    assert isinstance(nested_fields["field"], type(str))
