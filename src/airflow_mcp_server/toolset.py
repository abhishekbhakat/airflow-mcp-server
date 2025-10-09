"""Toolset utilities for the Airflow MCP server."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import aiohttp
from mcp import types

from airflow_mcp_server.openapi_parser import OperationDetails, OperationParser


@dataclass(slots=True)
class PreparedRequest:
    path: str
    query: dict[str, Any]
    body: dict[str, Any] | None


class AirflowOpenAPIToolset:
    """Generate MCP tool definitions from the Airflow OpenAPI specification."""

    def __init__(self, spec: dict[str, Any], allow_mutations: bool, session: aiohttp.ClientSession) -> None:
        self._parser = OperationParser(spec)
        self._allow_mutations = allow_mutations
        self._session = session
        self._tools: dict[str, tuple[types.Tool, OperationDetails]] = {}
        self._category_index: dict[str, list[str]] = {}
        self._build_tools()

    def _build_tools(self) -> None:
        for operation_id in self._parser.get_operations():
            details = self._parser.parse_operation(operation_id)
            method = details.method.upper()
            if not self._allow_mutations and method != "GET":
                continue

            input_schema = details.input_model.model_json_schema(ref_template="#/$defs/{model}")
            tool = types.Tool(
                name=operation_id,
                description=details.description,
                inputSchema=input_schema,
                outputSchema=None,
                _meta={"path": details.path, "method": method},
            )
            self._tools[operation_id] = (tool, details)

            tags = details.tags or ["General"]
            for tag in tags:
                self._category_index.setdefault(tag, []).append(operation_id)

    def list_tools(self) -> list[types.Tool]:
        return [tool for tool, _ in self._tools.values()]

    def get_tool(self, name: str) -> tuple[types.Tool, OperationDetails]:
        if name not in self._tools:
            raise ValueError(f"Unknown tool '{name}'")
        return self._tools[name]

    def list_categories(self) -> dict[str, list[str]]:
        return {category: sorted(tool_names) for category, tool_names in self._category_index.items()}

    def tools_for_category(self, category: str) -> list[types.Tool]:
        tool_names = self._category_index.get(category, [])
        return [self._tools[name][0] for name in tool_names if name in self._tools]

    def _field_alias(self, details: OperationDetails, field_name: str) -> str:
        field = details.input_model.model_fields.get(field_name)
        if field is None:
            return field_name
        return field.alias or field_name

    def _prepare_request(self, details: OperationDetails, arguments: dict[str, Any]) -> PreparedRequest:
        model_instance = details.input_model(**(arguments or {}))
        serialized = model_instance.model_dump(exclude_none=True, by_alias=True)

        parameter_mapping: dict[str, list[str]] = details.input_model.model_config.get("parameter_mapping", {})

        path_params: dict[str, Any] = {}
        for param_name in parameter_mapping.get("path", []):
            alias = self._field_alias(details, param_name)
            if alias not in serialized:
                raise ValueError(f"Missing required path parameter '{param_name}'")
            path_params[param_name] = serialized[alias]

        query_params: dict[str, Any] = {}
        for param_name in parameter_mapping.get("query", []):
            alias = self._field_alias(details, param_name)
            if alias in serialized:
                query_params[alias] = serialized[alias]

        body_params: dict[str, Any] = {}
        for param_name in parameter_mapping.get("body", []):
            alias = self._field_alias(details, param_name)
            if alias in serialized:
                body_params[alias] = serialized[alias]

        path = details.path
        for name, value in path_params.items():
            path = path.replace(f"{{{name}}}", str(value))

        sanitized_query = self._sanitize_query_params(query_params)

        return PreparedRequest(path=path, query=sanitized_query, body=body_params or None)

    def _sanitize_query_params(self, params: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}

        for key, value in params.items():
            if isinstance(value, bool):
                sanitized[key] = "true" if value else "false"
            elif isinstance(value, (list, tuple)):
                sanitized[key] = [self._stringify_query_value(item) for item in value]
            elif value is None:
                continue
            else:
                sanitized[key] = self._stringify_query_value(value)

        return sanitized

    def _stringify_query_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> list[types.TextContent] | tuple[list[types.TextContent], dict[str, Any]]:
        _, details = self.get_tool(name)
        request = self._prepare_request(details, arguments or {})

        async with self._session.request(
            details.method,
            request.path,
            params=request.query or None,
            json=request.body,
        ) as response:
            body = await response.read()
            content_type = response.headers.get("content-type", "")

            if response.status >= 400:
                payload = body.decode("utf-8", errors="ignore")
                raise ValueError(f"HTTP {response.status}: {payload}")

            if "application/json" in content_type.lower():
                if not body:
                    return ([], {})
                try:
                    parsed = json.loads(body.decode("utf-8"))
                except json.JSONDecodeError:
                    text = body.decode("utf-8", errors="replace")
                    return [types.TextContent(type="text", text=text)]
                return ([], parsed)

            text = body.decode("utf-8", errors="replace")
            return [types.TextContent(type="text", text=text)]
