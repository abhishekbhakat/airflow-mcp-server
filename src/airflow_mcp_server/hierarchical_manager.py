"""Hierarchical tool manager for dynamic tool discovery in Airflow MCP server."""

import logging

import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap

from .utils.category_mapper import extract_categories_from_openapi, filter_routes_by_methods, get_category_info, get_category_tools_info

logger = logging.getLogger(__name__)


class HierarchicalToolManager:
    """Manages dynamic tool state transitions for hierarchical discovery."""

    # Tools that are always available for navigation
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
        self.category_tool_instances = {}  # Store FastMCP instances for each category

        # DYNAMIC DISCOVERY: Extract categories from OpenAPI spec
        all_categories = extract_categories_from_openapi(openapi_spec)

        # Filter routes by allowed methods
        self.categories = {}
        for category, routes in all_categories.items():
            filtered_routes = filter_routes_by_methods(routes, self.allowed_methods)
            if filtered_routes:  # Only include categories with allowed routes
                self.categories[category] = filtered_routes

        logger.info(f"Discovered {len(self.categories)} categories with {sum(len(routes) for routes in self.categories.values())} total tools")

        # Initialize with persistent navigation tools
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
        # Validate category exists
        if category not in self.categories:
            available = ", ".join(self.categories.keys())
            return f"Category '{category}' not found. Available: {available}"

        # Remove current tools
        self._remove_current_tools()

        # Add category-specific tools
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
        # Remove individual tools (like category_info)
        tools_to_remove = self.current_tools - self.PERSISTENT_TOOLS
        for tool_name in tools_to_remove:
            try:
                self.mcp.remove_tool(tool_name)
                logger.debug(f"Removed tool: {tool_name}")
            except Exception as e:
                logger.warning(f"Failed to remove tool {tool_name}: {e}")

        # Unmount category API tools if any are mounted
        for category, mount_prefix in self.category_tool_instances.items():
            try:
                # Note: FastMCP doesn't have unmount, so we'll need to track this differently
                # For now, we'll leave them mounted but this could be improved
                logger.debug(f"Category {category} tools remain mounted under '{mount_prefix}'")
            except Exception as e:
                logger.warning(f"Failed to unmount {category} tools: {e}")

        # Keep persistent tools in current_tools
        self.current_tools = self.current_tools & self.PERSISTENT_TOOLS

    def _add_persistent_tools(self):
        """Add persistent navigation tools that are always available."""

        @self.mcp.tool()
        def browse_categories() -> str:
            """Show all available Airflow categories with tool counts."""
            return self.get_categories_info()

        @self.mcp.tool()
        def select_category(category: str) -> str:
            """Switch to tools for specific category.

            Args:
                category: Name of the category to explore
            """
            return self.switch_to_category(category)

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

        # Add info tool for the category
        @self.mcp.tool()
        def category_info() -> str:
            """Show information about current category tools."""
            return get_category_tools_info(category, routes)

        self.current_tools.add("category_info")

        # Generate actual API tools using FastMCP's OpenAPI capabilities
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
        # Create a filtered OpenAPI spec containing only this category's routes
        filtered_spec = self._create_filtered_openapi_spec(routes)

        # Create route maps based on allowed methods
        route_maps = [RouteMap(methods=list(self.allowed_methods), mcp_type=MCPType.TOOL)]

        # Create a category-specific FastMCP instance
        category_mcp = FastMCP.from_openapi(openapi_spec=filtered_spec, client=self.client, route_maps=route_maps)

        # Mount the category MCP as a subserver with category prefix
        category_prefix = category
        self.mcp.mount(category_prefix, category_mcp)

        # Store the mounted instance for cleanup later
        self.category_tool_instances[category] = category_prefix

        # Get the tool names that were created (they'll have the prefix)
        created_tools = []
        # Note: We can't easily get the exact tool names without accessing internals
        # But we know they exist and are accessible via the mount

        logger.info(f"Mounted {category} API tools under prefix '{category_prefix}'")
        return created_tools

    def _create_filtered_openapi_spec(self, routes: list[dict]) -> dict:
        """Create a filtered OpenAPI spec containing only the specified routes.

        Args:
            routes: List of route information to include

        Returns:
            Filtered OpenAPI specification
        """
        # Start with the base spec structure
        filtered_spec = {
            "openapi": self.openapi_spec.get("openapi", "3.0.0"),
            "info": self.openapi_spec.get("info", {"title": "Filtered API", "version": "1.0.0"}),
            "servers": self.openapi_spec.get("servers", []),
            "components": self.openapi_spec.get("components", {}),
            "paths": {},
        }

        # Add only the paths for the specified routes
        for route in routes:
            path = route["path"]
            method = route["method"].lower()

            # Initialize path if not exists
            if path not in filtered_spec["paths"]:
                filtered_spec["paths"][path] = {}

            # Copy the operation from original spec
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
