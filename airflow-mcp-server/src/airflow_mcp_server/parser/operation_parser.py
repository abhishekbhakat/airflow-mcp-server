import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from openapi_core import OpenAPI
from pydantic import BaseModel, create_model

logger = logging.getLogger(__name__)


@dataclass
class OperationDetails:
    """Details of an OpenAPI operation."""

    operation_id: str
    path: str
    method: str
    parameters: dict[str, Any]
    request_body: type[BaseModel] | None = None
    response_model: type[BaseModel] | None = None


class OperationParser:
    """Parser for OpenAPI operations."""

    def __init__(self, spec_path: Path | str | object) -> None:
        """Initialize parser with OpenAPI specification.

        Args:
            spec_path: Path to OpenAPI spec file or file-like object
        """
        # Load and parse OpenAPI spec
        if isinstance(spec_path, (str | Path)):
            with open(spec_path) as f:
                self.raw_spec = yaml.safe_load(f)
        else:
            self.raw_spec = yaml.safe_load(spec_path)

        # Initialize OpenAPI spec
        spec = OpenAPI.from_dict(self.raw_spec)
        self.spec = spec
        self._paths = self.raw_spec["paths"]
        self._components = self.raw_spec.get("components", {})
        self._schema_cache: dict[str, dict[str, Any]] = {}

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
            # Find operation in spec
            for path, path_item in self._paths.items():
                for method, operation in path_item.items():
                    if method.startswith("x-") or method == "parameters":
                        continue

                    if operation.get("operationId") == operation_id:
                        logger.debug("Found operation %s at %s %s", operation_id, method, path)

                        # Add path to operation for parameter context
                        operation["path"] = path
                        operation["path_item"] = path_item

                        # Extract operation details
                        parameters = self.extract_parameters(operation)
                        request_body = self._parse_request_body(operation)
                        response_model = self._parse_response_model(operation)

                        return OperationDetails(
                            operation_id=operation_id,
                            path=str(path),
                            method=method,
                            parameters=parameters,
                            request_body=request_body,
                            response_model=response_model,
                        )

            raise ValueError(f"Operation {operation_id} not found in spec")

        except Exception as e:
            logger.error("Error parsing operation %s: %s", operation_id, e)
            raise

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

        # Handle path-level parameters
        path_item = operation.get("path_item", {})
        if path_item and "parameters" in path_item:
            self._process_parameters(path_item["parameters"], parameters)

        # Handle operation-level parameters
        self._process_parameters(operation.get("parameters", []), parameters)

        return parameters

    def _process_parameters(self, params: list[dict[str, Any]], target: dict[str, dict[str, Any]]) -> None:
        """Process a list of parameters and add them to the target dict.

        Args:
            params: List of parameter objects
            target: Target dictionary to store processed parameters
        """
        for param in params:
            # Resolve parameter reference if needed
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"])

            # Validate parameter structure
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
        for part in parts[1:]:  # Skip first '#'
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

        return {
            "type": self._map_type(schema.get("type", "string")),
            "required": param.get("required", False),
            "default": schema.get("default"),
            "description": param.get("description"),
        }

    def _map_type(self, openapi_type: str) -> type:
        """Map OpenAPI type to Python type.

        Args:
            openapi_type: OpenAPI type string

        Returns:
            Corresponding Python type
        """
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        return type_map.get(openapi_type, Any)

    def _parse_request_body(self, operation: dict[str, Any]) -> type[BaseModel] | None:
        """Parse request body schema into Pydantic model.

        Args:
            operation: Operation object from OpenAPI spec

        Returns:
            Pydantic model for request body or None
        """
        if "requestBody" not in operation:
            return None

        content = operation["requestBody"].get("content", {})
        if "application/json" not in content:
            return None

        schema = content["application/json"].get("schema", {})
        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"])

        return self._create_model("RequestBody", schema)

    def _parse_response_model(self, operation: dict[str, Any]) -> type[BaseModel] | None:
        """Parse response schema into Pydantic model.

        Args:
            operation: Operation object from OpenAPI spec

        Returns:
            Pydantic model for response or None
        """
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

        return self._create_model("Response", schema)

    def _create_model(self, name: str, schema: dict[str, Any]) -> type[BaseModel]:
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

        if schema.get("type") != "object":
            raise ValueError("Schema must be an object type")

        fields = {}
        for prop_name, prop_schema in schema.get("properties", {}).items():
            # Resolve property schema reference if needed
            if "$ref" in prop_schema:
                prop_schema = self._resolve_ref(prop_schema["$ref"])

            if prop_schema.get("type") == "object":
                # Create nested model
                nested_model = self._create_model(f"{name}_{prop_name}", prop_schema)
                field_type = nested_model
            elif prop_schema.get("type") == "array":
                # Handle array types
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
                field_type = self._map_type(prop_schema.get("type", "string"))

            required = prop_name in schema.get("required", [])
            fields[prop_name] = (field_type, ... if required else None)

        logger.debug("Creating model %s with fields: %s", name, fields)
        try:
            return create_model(name, **fields)
        except Exception as e:
            logger.error("Error creating model %s: %s", name, e)
            raise ValueError(f"Failed to create model {name}: {e}")
