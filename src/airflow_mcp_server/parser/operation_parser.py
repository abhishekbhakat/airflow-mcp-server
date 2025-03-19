import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Union

import yaml
from openapi_core import OpenAPI
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)


@dataclass
class OperationDetails:
    """Details of an OpenAPI operation."""

    operation_id: str
    path: str
    method: str
    parameters: dict[str, Any]
    input_model: type[BaseModel]
    description: str


class OperationParser:
    """Parser for OpenAPI operations."""

    def __init__(self, spec_path: Path | str | dict | bytes | object) -> None:
        """Initialize parser with OpenAPI specification.

        Args:
            spec_path: Path to OpenAPI spec file, dict, bytes, or file-like object

        Raises:
            ValueError: If spec_path is invalid or spec cannot be loaded
        """
        try:
            if isinstance(spec_path, bytes):
                self.raw_spec = yaml.safe_load(spec_path)
            elif isinstance(spec_path, dict):
                self.raw_spec = spec_path
            elif isinstance(spec_path, str | Path):
                with open(spec_path) as f:
                    self.raw_spec = yaml.safe_load(f)
            elif hasattr(spec_path, "read"):
                self.raw_spec = yaml.safe_load(spec_path)
            else:
                raise ValueError(f"Invalid spec_path type: {type(spec_path)}. Expected Path, str, dict, bytes or file-like object")

            spec = OpenAPI.from_dict(self.raw_spec)
            self.spec = spec
            self._paths = self.raw_spec["paths"]
            self._components = self.raw_spec.get("components", {})
            self._schema_cache: dict[str, dict[str, Any]] = {}

        except Exception as e:
            logger.error("Error initializing OperationParser: %s", e)
            raise ValueError(f"Failed to initialize parser: {e}") from e

    def _merge_allof_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Merge an allOf schema into a single effective schema.

        Args:
            schema: The schema potentially containing allOf

        Returns:
            A merged schema with unified properties and required fields
        """
        if "allOf" not in schema:
            return schema
        merged = {"type": "object", "properties": {}, "required": []}
        for subschema in schema["allOf"]:
            resolved = subschema
            if "$ref" in subschema:
                resolved = self._resolve_ref(subschema["$ref"])
            if "properties" in resolved:
                merged["properties"].update(resolved["properties"])
            if "required" in resolved:
                merged["required"].extend(resolved.get("required", []))
        merged["required"] = list(set(merged["required"]))  # Remove duplicates
        logger.debug("Merged allOf schema: %s", merged)
        return merged

    def parse_operation(self, operation_id: str) -> OperationDetails:
        """Parse operation details from OpenAPI spec.

        Args:
            operation_id: Operation ID to parse

        Returns:
            OperationDetails object containing parsed information

        Raises:
            ValueError: If operation not found or invalid
        """
        try:
            for path, path_item in self._paths.items():
                for method, operation in path_item.items():
                    if method.startswith("x-") or method == "parameters":
                        continue

                    if operation.get("operationId") == operation_id:
                        logger.debug("Found operation %s at %s %s", operation_id, method, path)

                        operation["path"] = path
                        operation["path_item"] = path_item
                        description = operation.get("description") or operation.get("summary") or operation_id

                        parameters = self.extract_parameters(operation)

                        # Get request body schema if present
                        body_schema = None
                        if "requestBody" in operation:
                            content = operation["requestBody"].get("content", {})
                            if "application/json" in content:
                                body_schema = content["application/json"].get("schema", {})
                                if "$ref" in body_schema:
                                    body_schema = self._resolve_ref(body_schema["$ref"])

                        # Create unified input model
                        input_model = self._create_input_model(operation_id, parameters, body_schema)

                        return OperationDetails(operation_id=operation_id, path=str(path), method=method, parameters=parameters, description=description, input_model=input_model)

            raise ValueError(f"Operation {operation_id} not found in spec")

        except Exception as e:
            logger.error("Error parsing operation %s: %s", operation_id, e)
            raise

    def _create_input_model(
        self,
        operation_id: str,
        parameters: dict[str, Any],
        body_schema: dict[str, Any] | None = None,
    ) -> type[BaseModel]:
        """Create unified input model for all parameters."""
        fields: dict[str, tuple[type, Any]] = {}
        parameter_mapping = {"path": [], "query": [], "body": []}

        # Add path parameters
        for name, schema in parameters.get("path", {}).items():
            field_type = schema["type"]  # Use the mapped type from parameter schema
            fields[name] = (field_type | None, None)  # Make all optional
            parameter_mapping["path"].append(name)

        # Add query parameters
        for name, schema in parameters.get("query", {}).items():
            field_type = schema["type"]  # Use the mapped type from parameter schema
            fields[name] = (field_type | None, None)  # Make all optional
            parameter_mapping["query"].append(name)

        # Handle body schema with allOf support
        if body_schema:
            effective_schema = self._merge_allof_schema(body_schema)
            if "properties" in effective_schema or effective_schema.get("type") == "object":
                for prop_name, prop_schema in effective_schema.get("properties", {}).items():
                    field_type = self._map_type(prop_schema.get("type", "string"), prop_schema.get("format"), prop_schema)
                    default = None if prop_name in effective_schema.get("required", []) else None
                    if prop_name == "schema":  # Avoid shadowing BaseModel.schema
                        fields["connection_schema"] = (field_type | None, Field(default, alias="schema"))
                        parameter_mapping["body"].append("connection_schema")
                    else:
                        fields[prop_name] = (field_type | None, default)
                        parameter_mapping["body"].append(prop_name)

        logger.debug("Creating input model for %s with fields: %s", operation_id, fields)
        model = create_model(f"{operation_id}_input", **fields)
        model.model_config["parameter_mapping"] = parameter_mapping
        return model

    def extract_parameters(self, operation: dict[str, Any]) -> dict[str, Any]:
        """Extract and categorize operation parameters.

        Args:
            operation: Operation object from OpenAPI spec

        Returns:
            Dictionary of parameters by category (path, query, header)
        """
        parameters: dict[str, dict[str, Any]] = {
            "path": {},
            "query": {},
            "header": {},
        }

        path_item = operation.get("path_item", {})
        if path_item and "parameters" in path_item:
            self._process_parameters(path_item["parameters"], parameters)

        self._process_parameters(operation.get("parameters", []), parameters)

        return parameters

    def _process_parameters(self, params: list[dict[str, Any]], target: dict[str, dict[str, Any]]) -> None:
        """Process a list of parameters and add them to the target dict.

        Args:
            params: List of parameter objects
            target: Target dictionary to store processed parameters
        """
        for param in params:
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"])

            if not isinstance(param, dict) or "in" not in param:
                logger.warning("Invalid parameter format: %s", param)
                continue

            param_in = param["in"]
            if param_in in target:
                target[param_in][param["name"]] = self._map_parameter_schema(param)

    def _resolve_ref(self, ref: str) -> dict[str, Any]:
        """Resolve OpenAPI reference.

        Args:
            ref: Reference string (e.g. '#/components/schemas/Model')

        Returns:
            Resolved object
        """
        if ref in self._schema_cache:
            return self._schema_cache[ref]

        parts = ref.split("/")
        current = self.raw_spec
        for part in parts[1:]:
            current = current[part]

        self._schema_cache[ref] = current
        return current

    def _map_parameter_schema(self, param: dict[str, Any]) -> dict[str, Any]:
        """Map parameter schema to Python type information.

        Args:
            param: Parameter object from OpenAPI spec

        Returns:
            Dictionary with Python type information
        """
        schema = param.get("schema", {})
        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"])

        # Get the type and format from schema
        openapi_type = schema.get("type", "string")
        format_type = schema.get("format")

        return {
            "type": self._map_type(openapi_type, format_type, schema),  # Pass format_type and full schema
            "required": param.get("required", False),
            "default": schema.get("default"),
            "description": param.get("description"),
        }

    def _map_type(self, openapi_type: str, format_type: str | None = None, schema: dict[str, Any] | None = None) -> type:
        """Map OpenAPI type to Python type."""
        # Handle enums
        if schema and "enum" in schema:
            return Literal[tuple(schema["enum"])]  # type: ignore

        # Handle date-time format
        if openapi_type == "string" and format_type == "date-time":
            return datetime

        # Handle nullable fields
        base_type = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }.get(openapi_type, Any)

        if schema and schema.get("nullable"):
            return Union[base_type, None]  # noqa: UP007

        return base_type

    def _parse_response_model(self, operation: dict[str, Any]) -> type[BaseModel] | None:
        """Parse response schema into Pydantic model."""
        try:
            responses = operation.get("responses", {})
            if "200" not in responses:
                return None

            response = responses["200"]
            if "$ref" in response:
                response = self._resolve_ref(response["$ref"])

            content = response.get("content", {})
            if "application/json" not in content:
                return None

            schema = content["application/json"].get("schema", {})
            if "$ref" in schema:
                schema = self._resolve_ref(schema["$ref"])

            logger.debug("Response schema before model creation: %s", schema)

            # Ensure schema has properties
            if "properties" not in schema:
                logger.error("Response schema missing properties")
                return None

            # Create model with schema properties
            model = self._create_model("Response", schema)
            logger.debug("Created response model with schema: %s", model.model_json_schema())
            return model

        except Exception as e:
            logger.error("Failed to create response model: %s", e)
            return None

    def _create_model(self, name: str, schema: dict[str, Any]) -> type[BaseModel]:  # noqa C901
        """Create Pydantic model from schema.

        Args:
            name: Model name
            schema: OpenAPI schema

        Returns:
            Generated Pydantic model

        Raises:
            ValueError: If schema is invalid
        """
        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"])

        # Handle discriminated unions
        if "anyOf" in schema:
            discriminator = schema.get("discriminator", {}).get("propertyName")
            if discriminator:
                union_types = []
                for subschema in schema["anyOf"]:
                    if "$ref" in subschema:
                        resolved = self._resolve_ref(subschema["$ref"])
                        sub_model = self._create_model(f"{name}_type", resolved)
                        union_types.append(sub_model)

                fields = {
                    "type_name": (str, ...),  # Use type_name instead of __type
                    **{k: (Union[tuple(union_types)], ...) for k in schema.get("properties", {}) if k != discriminator},  # noqa: UP007
                }
                return create_model(name, **fields)

        if schema.get("type", "object") != "object":
            raise ValueError("Schema must be an object type")

        fields = {}
        for prop_name, prop_schema in schema.get("properties", {}).items():
            if "$ref" in prop_schema:
                prop_schema = self._resolve_ref(prop_schema["$ref"])

            required = prop_name in schema.get("required", [])

            if prop_schema.get("type") == "object":
                nested_model = self._create_model(f"{name}_{prop_name}", prop_schema)
                field_type = nested_model
            elif prop_schema.get("type") == "array":
                items = prop_schema.get("items", {})
                if "$ref" in items:
                    items = self._resolve_ref(items["$ref"])
                if items.get("type") == "object":
                    item_model = self._create_model(f"{name}_{prop_name}_item", items)
                    field_type = list[item_model]
                else:
                    item_type = self._map_type(items.get("type", "string"))
                    field_type = list[item_type]
            else:
                field_type = self._map_type(prop_schema.get("type", "string"), prop_schema.get("format"), prop_schema)

                # Add validation parameters
                field_config = {}
                if "pattern" in prop_schema:
                    field_config["pattern"] = prop_schema["pattern"]
                if "minLength" in prop_schema:
                    field_config["min_length"] = prop_schema["minLength"]
                if "maxLength" in prop_schema:
                    field_config["max_length"] = prop_schema["maxLength"]
                if "minimum" in prop_schema:
                    field_config["ge"] = prop_schema["minimum"]
                if "maximum" in prop_schema:
                    field_config["le"] = prop_schema["maximum"]

                # Create field with validation
                if field_config:
                    field = Field(..., **field_config) if required else Field(None, **field_config)
                    fields[prop_name] = (field_type, field)
                    continue

            fields[prop_name] = (field_type, ... if required else None)

        logger.debug("Creating model %s with fields: %s", name, fields)
        try:
            return create_model(name, **fields)
        except Exception as e:
            logger.error("Error creating model %s: %s", name, e)
            raise ValueError(f"Failed to create model {name}: {e}")

    def get_operations(self) -> list[str]:
        """Get list of all operation IDs from spec."""
        operations = []

        for path in self._paths.values():
            for method, operation in path.items():
                if method.startswith("x-") or method == "parameters":
                    continue
                if "operationId" in operation:
                    operations.append(operation["operationId"])

        return operations
