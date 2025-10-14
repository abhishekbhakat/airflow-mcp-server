"""Hierarchical tool manager for dynamic discovery using the low-level MCP server."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from mcp import types
from mcp.server.lowlevel import Server

from airflow_mcp_server.toolset import AirflowOpenAPIToolset
from airflow_mcp_server.utils.category_mapper import (
    extract_categories_from_openapi,
    filter_routes_by_methods,
    get_category_info,
    get_category_tools_info,
    get_tool_name_from_route,
)

logger = logging.getLogger(__name__)


class HierarchicalToolManager:
    """Registers hierarchical navigation tools with the MCP server."""

    NAVIGATION_TOOLS = {"browse_categories", "select_category", "get_current_category", "back_to_categories"}

    def __init__(
        self,
        server: Server,
        toolset: AirflowOpenAPIToolset,
        openapi_spec: dict[str, Any],
        allowed_methods: set[str],
    ) -> None:
        self._server = server
        self._toolset = toolset
        self._allowed_methods = allowed_methods
        self._session_state_attr = "_airflow_category_state"

        all_categories = extract_categories_from_openapi(openapi_spec)
        categories: dict[str, list[dict[str, Any]]] = {}
        for category, routes in all_categories.items():
            filtered = filter_routes_by_methods(routes, allowed_methods)
            if filtered:
                categories[category] = filtered

        self._categories = categories
        self._category_tool_names: dict[str, list[str]] = {
            category: [get_tool_name_from_route(route) for route in routes]
            for category, routes in categories.items()
        }
        self._default_category = "DAG" if "DAG" in self._categories else None

        self._navigation_tools = self._build_navigation_tools()
        self._register_handlers()

        logger.info(
            "Hierarchical manager ready with %d categories / %d tools",
            len(self._categories),
            sum(len(routes) for routes in self._categories.values()),
        )

    def _build_navigation_tools(self) -> dict[str, types.Tool]:
        base_schema = {"type": "object", "properties": {}, "additionalProperties": False}
        category_schema = {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category name returned by browse_categories",
                }
            },
            "required": ["category"],
            "additionalProperties": False,
        }

        return {
            "browse_categories": types.Tool(
                name="browse_categories",
                description="Show all available Airflow categories with tool counts",
                inputSchema=base_schema,
                outputSchema=None,
            ),
            "select_category": types.Tool(
                name="select_category",
                description="Switch to the tools for a specific category",
                inputSchema=category_schema,
                outputSchema=None,
            ),
            "get_current_category": types.Tool(
                name="get_current_category",
                description="Get the currently selected category",
                inputSchema=base_schema,
                outputSchema=None,
            ),
            "back_to_categories": types.Tool(
                name="back_to_categories",
                description="Return to browsing all categories",
                inputSchema=base_schema,
                outputSchema=None,
            ),
        }

    def _register_handlers(self) -> None:
        navigation_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[list[types.TextContent]]]] = {
            "browse_categories": self._handle_browse,
            "select_category": self._handle_select,
            "get_current_category": self._handle_get_current,
            "back_to_categories": self._handle_reset,
        }

        @self._server.list_tools()
        async def _list_tools(_: types.ListToolsRequest | None = None) -> types.ListToolsResult:
            session_state = self._ensure_session_state()
            selected = session_state["category"]

            tools = list(self._navigation_tools.values())
            if selected and selected in self._category_tool_names:
                for name in self._category_tool_names[selected]:
                    try:
                        tool, _details = self._toolset.get_tool(name)
                        tools.append(tool)
                    except ValueError:
                        logger.debug("Tool %s not found when listing category %s", name, selected)

            return types.ListToolsResult(tools=tools)

        @self._server.call_tool()
        async def _call_tool(tool_name: str, arguments: dict[str, Any]):
            handler = navigation_handlers.get(tool_name)
            if handler:
                return await handler(arguments or {})

            try:
                return await self._toolset.call_tool(tool_name, arguments or {})
            except ValueError as exc:
                return [types.TextContent(type="text", text=str(exc))]

    async def _handle_browse(self, _: dict[str, Any]) -> list[types.TextContent]:
        info = get_category_info(self._categories)
        return [types.TextContent(type="text", text=info)]

    async def _handle_select(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        category = arguments.get("category")
        if not category:
            return [types.TextContent(type="text", text="Missing required argument 'category'")]
        message = await self._select_category(str(category))
        return [types.TextContent(type="text", text=message)]

    async def _handle_get_current(self, _: dict[str, Any]) -> list[types.TextContent]:
        session_state = self._ensure_session_state()
        selected = session_state["category"]
        if selected and selected in self._categories:
            summary = get_category_tools_info(selected, self._categories[selected])
            return [types.TextContent(type="text", text=summary)]
        return [types.TextContent(type="text", text="No category selected. Use browse_categories() to explore.")]

    async def _handle_reset(self, _: dict[str, Any]) -> list[types.TextContent]:
        message = await self._reset_category()
        return [types.TextContent(type="text", text=message)]

    def _ensure_session_state(self) -> dict[str, str | None]:
        session = self._server.request_context.session
        state = cast(dict[str, str | None] | None, getattr(session, self._session_state_attr, None))
        if state is None:
            state = {"category": self._default_category}
            setattr(session, self._session_state_attr, state)
        return state

    async def _select_category(self, category: str) -> str:
        if category not in self._categories:
            available = ", ".join(sorted(self._categories.keys())) or "none"
            return f"Category '{category}' not found. Available categories: {available}"

        session_state = self._ensure_session_state()
        session_state["category"] = category

        try:
            await self._server.request_context.session.send_tool_list_changed()
        except Exception as exc:  # pragma: no cover - notification failure path
            logger.debug("Failed to send tool list changed notification: %s", exc)

        summary = get_category_tools_info(category, self._categories[category])
        return summary

    async def _reset_category(self) -> str:
        session_state = self._ensure_session_state()
        session_state["category"] = None
        try:
            await self._server.request_context.session.send_tool_list_changed()
        except Exception as exc:  # pragma: no cover - notification failure path
            logger.debug("Failed to send tool list changed notification: %s", exc)
        return "Returned to category browser. Use browse_categories() to pick a new category."
