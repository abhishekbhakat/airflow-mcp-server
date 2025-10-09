"""Utilities for parsing Airflow's OpenAPI specification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Literal, cast

import yaml
from pydantic import BaseModel, Field, create_model


@dataclass(slots=True)
class OperationDetails:
    """Structure describing a single OpenAPI operation."""

    operation_id: str
    path: str
    method: str
    parameters: dict[str, Any]
    input_model: type[BaseModel]
    description: str
    tags: list[str]


class OperationParser:
    """Parse an OpenAPI specification into callable operation details."""

    def __init__(self, spec_source: Path | str | dict[str, Any] | bytes | IO[str] | IO[bytes]) -> None:
        if isinstance(spec_source, bytes):
            self.raw_spec = yaml.safe_load(spec_source)
        elif isinstance(spec_source, dict):
            self.raw_spec = spec_source
        elif isinstance(spec_source, (str, Path)):
            with open(spec_source, encoding="utf-8") as fh:
                self.raw_spec = yaml.safe_load(fh)
        elif hasattr(spec_source, "read"):
            self.raw_spec = yaml.safe_load(cast(IO[Any], spec_source))
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported spec source type: {type(spec_source)}")

        if not isinstance(self.raw_spec, dict):
            raise ValueError("OpenAPI spec must be a mapping")

        try:
            self._paths = self.raw_spec["paths"]
        except KeyError as exc:  # pragma: no cover - invalid spec
            raise ValueError("OpenAPI spec missing 'paths' section") from exc

        self._components = self.raw_spec.get("components", {})
        self._schema_cache: dict[str, dict[str, Any]] = {}

    def get_operations(self) -> list[str]:
        operations: list[str] = []
        for path_item in self._paths.values():
            for method, operation in path_item.items():
                if method.startswith("x-") or method == "parameters":
                    continue
                operation_id = operation.get("operationId")
                if operation_id:
                    operations.append(operation_id)
        return operations

    def parse_operation(self, operation_id: str) -> OperationDetails:
        for path, path_item in self._paths.items():
            for method, operation in path_item.items():
                if method.startswith("x-") or method == "parameters":
                    continue

                if operation.get("operationId") != operation_id:
                    continue

                operation["path"] = path
                operation["path_item"] = path_item
                description = operation.get("description") or operation.get("summary") or operation_id
                parameters = self._extract_parameters(operation)

                body_schema = None
                if "requestBody" in operation:
                    content = operation["requestBody"].get("content", {})
                    if "application/json" in content:
                        body_schema = content["application/json"].get("schema", {})
                        if "$ref" in body_schema:
                            body_schema = self._resolve_ref(body_schema["$ref"])

                input_model = self._create_input_model(operation_id, parameters, body_schema)

                tags = [tag for tag in operation.get("tags", []) if isinstance(tag, str)]

                return OperationDetails(
                    operation_id=operation_id,
                    path=str(path),
                    method=str(method).upper(),
                    parameters=parameters,
                    input_model=input_model,
                    description=description,
                    tags=tags,
                )

        raise ValueError(f"Operation {operation_id} not found in spec")

    def _extract_parameters(self, operation: dict[str, Any]) -> dict[str, Any]:
        parameters: dict[str, dict[str, Any]] = {"path": {}, "query": {}, "header": {}}

        path_item = operation.get("path_item", {})
        if path_item and "parameters" in path_item:
            self._process_parameters(path_item["parameters"], parameters)

        self._process_parameters(operation.get("parameters", []), parameters)

        return parameters

    def _process_parameters(self, params: list[dict[str, Any]], target: dict[str, dict[str, Any]]) -> None:
        for param in params or []:
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"])

            if not isinstance(param, dict) or "in" not in param:
                continue

            param_in = param["in"]
            if param_in in target:
                target[param_in][param["name"]] = self._map_parameter_schema(param)

    def _resolve_ref(self, ref: str) -> dict[str, Any]:
        if ref in self._schema_cache:
            return self._schema_cache[ref]

        parts = ref.split("/")
        current = self.raw_spec
        for part in parts[1:]:
            current = current[part]

        self._schema_cache[ref] = current
        return current

    def _map_parameter_schema(self, param: dict[str, Any]) -> dict[str, Any]:
        schema = param.get("schema", {})
        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"])

        openapi_type = schema.get("type", "string")
        format_type = schema.get("format")

        field_type, nullable = self._map_type(openapi_type, format_type, schema)

        return {
            "type": field_type,
            "nullable": nullable,
            "required": param.get("required", False),
            "default": schema.get("default"),
            "description": param.get("description"),
        }

    def _map_type(
        self,
        openapi_type: str,
        format_type: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> tuple[Any, bool]:
        nullable = bool(schema and schema.get("nullable"))

        mapping: dict[str, Any] = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        if schema and "enum" in schema:
            literal_type = Literal[tuple(schema["enum"])]
            return literal_type, nullable

        if openapi_type == "string" and format_type == "date-time":
            return (str, nullable)

        return (mapping.get(openapi_type, Any), nullable)

    def _merge_allof_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
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
        merged["required"] = list({*merged["required"]})
        return merged

    def _create_input_model(
        self,
        operation_id: str,
        parameters: dict[str, Any],
        body_schema: dict[str, Any] | None = None,
    ) -> type[BaseModel]:
        fields: dict[str, tuple[Any, Any]] = {}
        parameter_mapping = {"path": [], "query": [], "body": []}

        for name, schema in parameters.get("path", {}).items():
            field_type = schema["type"]
            default_value: Any = ... if schema.get("required") else None
            annotation: Any = field_type
            if schema.get("nullable") or not schema.get("required"):
                annotation = Any
            fields[name] = (annotation, default_value)
            parameter_mapping["path"].append(name)

        for name, schema in parameters.get("query", {}).items():
            field_type = schema["type"]
            default_value = ... if schema.get("required") else None
            annotation = field_type
            if schema.get("nullable") or not schema.get("required"):
                annotation = Any
            fields[name] = (annotation, default_value)
            parameter_mapping["query"].append(name)

        if body_schema:
            effective_schema = self._merge_allof_schema(body_schema)
            if "properties" in effective_schema or effective_schema.get("type") == "object":
                for prop_name, prop_schema in effective_schema.get("properties", {}).items():
                    field_type, nullable = self._map_type(
                        prop_schema.get("type", "string"),
                        prop_schema.get("format"),
                        prop_schema,
                    )
                    required = prop_name in effective_schema.get("required", [])
                    default_value = ... if required else None
                    annotation = field_type
                    if nullable or not required:
                        annotation = Any
                    if prop_name == "schema":
                        fields["connection_schema"] = (
                            annotation,
                            Field(default=default_value, alias="schema"),
                        )
                        parameter_mapping["body"].append("connection_schema")
                    else:
                        fields[prop_name] = (annotation, default_value)
                        parameter_mapping["body"].append(prop_name)

        model = create_model(f"{operation_id}_input", **fields)  # type: ignore[arg-type]
        model.model_config["parameter_mapping"] = parameter_mapping
        return model
