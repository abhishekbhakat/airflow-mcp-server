"""Hierarchical tool manager for dynamic tool discovery in Airflow MCP server."""

import logging

import httpx
from fastmcp import Context, FastMCP
from fastmcp.server.openapi import MCPType, RouteMap

from airflow_mcp_server.utils.category_mapper import extract_categories_from_openapi, filter_routes_by_methods, get_category_info, get_category_tools_info

logger = logging.getLogger(__name__)


class HierarchicalToolManager:
    """Manages dynamic tool state transitions for hierarchical discovery."""

    PERSISTENT_TOOLS = {"browse_categories", "select_category", "get_current_category"}

    def __init__(self, mcp: FastMCP, openapi_spec: dict, client: httpx.AsyncClient, allowed_methods: set[str] | None = None):
        """Initialize hierarchical tool manager.

        Args:
            mcp: FastMCP server instance
            openapi_spec: OpenAPI specification dictionary
            client: HTTP client for API calls
            allowed_methods: Set of allowed HTTP methods (e.g., {"GET"} for safe mode)
        """
        self.mcp = mcp
        self.openapi_spec = openapi_spec
        self.client = client
        self.allowed_methods = allowed_methods or {"GET", "POST", "PUT", "DELETE", "PATCH"}
        self.current_mode = "categories"
        self.current_tools = set()
        self.category_tool_instances = {}

        all_categories = extract_categories_from_openapi(openapi_spec)

        self.categories = {}
        for category, routes in all_categories.items():
            filtered_routes = filter_routes_by_methods(routes, self.allowed_methods)
            if filtered_routes:
                self.categories[category] = filtered_routes

        logger.info(f"Discovered {len(self.categories)} categories with {sum(len(routes) for routes in self.categories.values())} total tools")

        self._add_persistent_tools()

    def get_categories_info(self) -> str:
        """Get formatted information about all available categories."""
        return get_category_info(self.categories)

    def switch_to_category(self, category: str) -> str:
        """Switch to tools for specific category.

        Args:
            category: Category name to switch to

        Returns:
            Status message
        """
        if category not in self.categories:
            available = ", ".join(self.categories.keys())
            return f"Category '{category}' not found. Available: {available}"

        self._remove_current_tools()

        self._add_category_tools(category)
        self.current_mode = category

        routes_count = len(self.categories[category])
        return f"Switched to {category} tools ({routes_count} available). Navigation tools always available."

    def get_current_category(self) -> str:
        """Get currently selected category.

        Returns:
            Current category status
        """
        if self.current_mode == "categories":
            return "No category selected. Currently browsing all categories."
        else:
            routes_count = len(self.categories[self.current_mode])
            return f"Currently selected category: {self.current_mode} ({routes_count} tools available)"

    def _remove_current_tools(self):
        """Remove category-specific tools but keep persistent navigation tools."""
        tools_to_remove = self.current_tools - self.PERSISTENT_TOOLS
        for tool_name in tools_to_remove:
            try:
                self.mcp.remove_tool(tool_name)
                logger.debug(f"Removed tool: {tool_name}")
            except Exception as e:
                logger.warning(f"Failed to remove tool {tool_name}: {e}")

        for category, mount_prefix in self.category_tool_instances.items():
            try:
                logger.debug(f"Category {category} tools remain mounted under '{mount_prefix}'")
            except Exception as e:
                logger.warning(f"Failed to unmount {category} tools: {e}")

        self.current_tools = self.current_tools & self.PERSISTENT_TOOLS

    def _add_persistent_tools(self):
        """Add persistent navigation tools that are always available."""

        @self.mcp.tool()
        def browse_categories() -> str:
            """Show all available Airflow categories with tool counts."""
            return self.get_categories_info()

        @self.mcp.tool()
        async def select_category(category: str, ctx: Context) -> str:
            """Switch to tools for specific category.

            Args:
                category: Name of the category to explore
            """
            result = self.switch_to_category(category)

            try:
                await ctx.session.send_tool_list_changed()
                logger.info(f"Sent tools/list_changed notification after selecting category: {category}")
            except Exception as e:
                logger.warning(f"Failed to send tool list notification: {e}")

            return result

        @self.mcp.tool()
        def get_current_category() -> str:
            """Get currently selected category."""
            return self.get_current_category()

        self.current_tools.update(self.PERSISTENT_TOOLS)

        logger.info(f"Added persistent navigation tools: {self.PERSISTENT_TOOLS}")

    def _add_category_tools(self, category: str):
        """Add tools for specific category using FastMCP's OpenAPI tool generation.

        Args:
            category: Category name
        """
        routes = self.categories[category]

        @self.mcp.tool()
        def category_info() -> str:
            """Show information about current category tools."""
            return get_category_tools_info(category, routes)

        self.current_tools.add("category_info")

        category_tools = self._create_category_api_tools(category, routes)

        logger.info(f"Added {category} tools: category_info + {len(category_tools)} API tools (persistent navigation always available)")

    def _create_category_api_tools(self, category: str, routes: list[dict]) -> list[str]:
        """Create actual API tools for a category using FastMCP's composition features.

        Args:
            category: Category name
            routes: List of route information for the category

        Returns:
            List of created tool names
        """
        filtered_spec = self._create_filtered_openapi_spec(routes)

        route_maps = [RouteMap(methods=list(self.allowed_methods), mcp_type=MCPType.TOOL)]

        category_mcp = FastMCP.from_openapi(openapi_spec=filtered_spec, client=self.client, route_maps=route_maps)

        category_prefix = category
        self.mcp.mount(category_prefix, category_mcp)

        self.category_tool_instances[category] = category_prefix

        created_tools = []

        logger.info(f"Mounted {category} API tools under prefix '{category_prefix}'")
        return created_tools

    def _create_filtered_openapi_spec(self, routes: list[dict]) -> dict:
        """Create a filtered OpenAPI spec containing only the specified routes.

        Args:
            routes: List of route information to include

        Returns:
            Filtered OpenAPI specification
        """
        filtered_spec = {
            "openapi": self.openapi_spec.get("openapi", "3.0.0"),
            "info": self.openapi_spec.get("info", {"title": "Filtered API", "version": "1.0.0"}),
            "servers": self.openapi_spec.get("servers", []),
            "components": self.openapi_spec.get("components", {}),
            "paths": {},
        }

        for route in routes:
            path = route["path"]
            method = route["method"].lower()

            if path not in filtered_spec["paths"]:
                filtered_spec["paths"][path] = {}

            if path in self.openapi_spec.get("paths", {}):
                original_path = self.openapi_spec["paths"][path]
                if method in original_path:
                    filtered_spec["paths"][path][method] = original_path[method]

        return filtered_spec

    def get_current_state(self) -> dict:
        """Get current state information for debugging.

        Returns:
            Dictionary with current state info
        """
        return {"mode": self.current_mode, "current_tools": list(self.current_tools), "total_categories": len(self.categories), "allowed_methods": list(self.allowed_methods)}
