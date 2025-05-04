import json
import pytest
from typing import Any
from pydantic import BaseModel
from airflow_mcp_server.parser.operation_parser import OperationDetails, OperationParser


@pytest.fixture
def parser() -> OperationParser:
    """Create OperationParser instance from tests/parser/openapi.json."""
    with open("tests/parser/openapi.json") as f:
        spec_dict = json.load(f)
    return OperationParser(spec_dict)


def test_parse_operation_basic(parser: OperationParser) -> None:
    """Test basic operation parsing."""
    operation = parser.parse_operation("get_dags")

    assert isinstance(operation, OperationDetails)
    assert operation.operation_id == "get_dags"
    assert operation.path == "/api/v2/dags"
    assert operation.method == "get"
    assert operation.description == "Get all DAGs."
    assert isinstance(operation.parameters, dict)


def test_parse_operation_with_no_description_but_summary(parser: OperationParser) -> None:
    """Test parsing operation with no description but summary."""
    operation = parser.parse_operation("get_connections")

    assert isinstance(operation, OperationDetails)
    assert operation.operation_id == "get_connections"
    assert operation.path == "/api/v2/connections"
    assert operation.method == "get"
    assert operation.description == "Get all connection entries."
    assert isinstance(operation.parameters, dict)


def test_parse_operation_with_path_params(parser: OperationParser) -> None:
    """Test parsing operation with path parameters."""
    operation = parser.parse_operation("get_dag")

    assert operation.path == "/api/v2/dags/{dag_id}"
    assert isinstance(operation.input_model, type(BaseModel))

    # Verify path parameter field exists
    fields = operation.input_model.__annotations__
    assert "dag_id" in fields
    assert str in fields["dag_id"].__args__  # Check if str is in the Union types

    # Verify parameter is mapped correctly
    assert "dag_id" in operation.input_model.model_config["parameter_mapping"]["path"]


def test_parse_operation_with_query_params(parser: OperationParser) -> None:
    """Test parsing operation with query parameters."""
    operation = parser.parse_operation("get_dags")

    # Verify query parameter field exists
    fields = operation.input_model.__annotations__
    assert "limit" in fields
    assert int in fields["limit"].__args__  # Check if int is in the Union types

    # Verify parameter is mapped correctly
    assert "limit" in operation.input_model.model_config["parameter_mapping"]["query"]


def test_parse_operation_with_body_params(parser: OperationParser) -> None:
    """Test parsing operation with request body."""
    # Find the correct operationId for posting a dag run in the OpenAPI spec
    # From the spec, the likely operation is under /api/v2/dags/{dag_id}/dagRuns
    # Let's use "post_dag_run" if it exists, otherwise use the actual operationId
    operation = parser.parse_operation("trigger_dag_run")

    # Verify body fields exist
    fields = operation.input_model.__annotations__
    assert "dag_run_id" in fields
    assert str in fields["dag_run_id"].__args__  # Check if str is in the Union types

    # Verify parameter is mapped correctly
    assert "dag_run_id" in operation.input_model.model_config["parameter_mapping"]["body"]


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
    # Check that str is in the Union types
    assert str in result["type"].__args__
    assert None.__class__ in result["type"].__args__  # Check for NoneType
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


def test_parse_operation_with_allof_body(parser: OperationParser) -> None:
    """Test parsing operation with allOf schema in request body."""
    operation = parser.parse_operation("test_connection")

    assert isinstance(operation, OperationDetails)
    assert operation.operation_id == "test_connection"
    assert operation.path == "/api/v2/connections/test"
    assert operation.method == "post"

    # Verify input model includes fields from allOf schema
    fields = operation.input_model.__annotations__
    assert "connection_id" in fields, "Missing connection_id from ConnectionCollectionItem"
    assert str in fields["connection_id"].__args__, "connection_id should be a string"
    assert "password" in fields, "Missing password from Connection"
    assert str in fields["password"].__args__, "password should be a string"
    assert "connection_schema" in fields, "Missing schema field (aliased as connection_schema)"
    assert str in fields["connection_schema"].__args__, "connection_schema should be a string"

    # Verify parameter mapping
    mapping = operation.input_model.model_config["parameter_mapping"]
    assert "body" in mapping
    assert "connection_id" in mapping["body"]
    assert "password" in mapping["body"]
    assert "connection_schema" in mapping["body"]

    # Verify alias configuration
    model_fields = operation.input_model.model_fields
    assert "connection_schema" in model_fields
    assert model_fields["connection_schema"].alias == "schema", "connection_schema should alias to schema"
