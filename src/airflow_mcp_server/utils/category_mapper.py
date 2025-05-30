"""Category mapping utilities for Airflow OpenAPI endpoints."""


def extract_categories_from_openapi(openapi_spec: dict) -> dict[str, list[dict]]:
    """Extract categories and their routes from OpenAPI spec.

    Args:
        openapi_spec: OpenAPI specification dictionary

    Returns:
        Dictionary mapping category names to lists of route info
    """
    categories = {}

    if "paths" not in openapi_spec:
        return categories

    for path, methods in openapi_spec["paths"].items():
        for method, operation in methods.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                # Extract tags (categories) from operation
                tags = operation.get("tags", ["Uncategorized"])

                route_info = {
                    "path": path,
                    "method": method.upper(),
                    "operation_id": operation.get("operationId", ""),
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "tags": tags,
                }

                # Add to each category
                for tag in tags:
                    if tag not in categories:
                        categories[tag] = []
                    categories[tag].append(route_info)

    return categories


def get_category_info(categories: dict[str, list[dict]]) -> str:
    """Get formatted category information with counts.

    Args:
        categories: Dictionary of categories and their routes

    Returns:
        Formatted string with category information
    """
    if not categories:
        return "No categories found."

    lines = ["Available Airflow Categories:\n"]

    # Sort categories by tool count (descending)
    sorted_categories = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)

    for category, routes in sorted_categories:
        count = len(routes)
        lines.append(f"- {category}: {count} tools")

    lines.append(f"\nTotal: {len(categories)} categories, {sum(len(routes) for routes in categories.values())} tools")
    lines.append('\nUse select_category("Category Name") to explore specific tools.')

    return "\n".join(lines)


def get_category_tools_info(category: str, routes: list[dict]) -> str:
    """Get formatted information about tools in a specific category.

    Args:
        category: Category name
        routes: List of route information for the category

    Returns:
        Formatted string with category tools information
    """
    lines = [f"{category} Tools ({len(routes)} available):\n"]

    # Group by method for better organization
    methods_groups = {}
    for route in routes:
        method = route["method"]
        if method not in methods_groups:
            methods_groups[method] = []
        methods_groups[method].append(route)

    # Display by method type
    for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
        if method in methods_groups:
            lines.append(f"\n{method} Operations:")

            for route in methods_groups[method]:
                operation_id = route["operation_id"]
                summary = route["summary"] or route["description"] or "No description"
                # Truncate long summaries
                if len(summary) > 80:
                    summary = summary[:77] + "..."
                lines.append(f"  - {operation_id}: {summary}")

    lines.append("\nUse back_to_categories() to return to category browser.")

    return "\n".join(lines)


def filter_routes_by_methods(routes: list[dict], allowed_methods: set[str]) -> list[dict]:
    """Filter routes by allowed HTTP methods.

    Args:
        routes: List of route information
        allowed_methods: Set of allowed HTTP methods (e.g., {"GET"})

    Returns:
        Filtered list of routes
    """
    return [route for route in routes if route["method"] in allowed_methods]


def get_tool_name_from_route(route: dict) -> str:
    """Generate a tool name from route information.

    Args:
        route: Route information dictionary

    Returns:
        Generated tool name
    """
    operation_id = route.get("operation_id", "")
    if operation_id:
        return operation_id

    # Fallback: generate from path and method
    path = route["path"].replace("/", "_").replace("{", "").replace("}", "")
    method = route["method"].lower()
    return f"{method}{path}"
