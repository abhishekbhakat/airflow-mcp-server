from __future__ import annotations

import asyncio
import logging

import httpx
from airflow.plugins_manager import AirflowPlugin
from fastmcp.experimental.server.openapi import (
    FastMCPOpenAPI,
    MCPType,
    RouteMap,
)
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


def _compute_airflow_prefix(request: Request) -> str:
    """Detect deployment path prefix (e.g., Astronomer's '/<deployment>') and drop '/mcp'.

    Prefers 'X-Forwarded-Prefix' header when present, otherwise uses ASGI root_path.
    Ensures the returned prefix does not include the plugin mount ('/mcp').
    """
    # Starlette headers are case-insensitive
    forwarded_prefix = request.headers.get("x-forwarded-prefix") or ""
    root_path = request.scope.get("root_path") or ""

    prefix = forwarded_prefix or root_path or ""
    if prefix.endswith("/"):
        prefix = prefix[:-1]
    if prefix.endswith("/mcp"):
        prefix = prefix[: -len("/mcp")] or ""
    return prefix


class StatelessMCPMount:
    """FastAPI-compatible object that creates a stateless MCP server.

    Every request must include Authorization: Bearer <token>.
    The token is forwarded to Airflow APIs for that specific request.
    Uses static tools (no hierarchical discovery) and stateless HTTP.
    """

    def __init__(self, path: str = "/mcp") -> None:
        self._path = path
        self._openapi_spec: dict | None = None
        self._spec_lock = asyncio.Lock()

    async def _ensure_openapi_spec(self, base_url: str, token: str) -> dict | None:
        """Fetch OpenAPI spec once and cache it."""
        if self._openapi_spec is not None:
            return self._openapi_spec

        async with self._spec_lock:
            if self._openapi_spec is not None:
                return self._openapi_spec

            client = httpx.AsyncClient(
                base_url=base_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )
            try:
                resp = await client.get("openapi.json")
                resp.raise_for_status()
                self._openapi_spec = resp.json()
                return self._openapi_spec
            except Exception as e:
                logger.error(f"Failed to fetch OpenAPI spec: {e}")
                return None
            finally:
                await client.aclose()

    async def _build_stateless_app(self, request: Request) -> Starlette:
        """Build a stateless MCP app that forwards the current request's auth token."""
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            async def auth_error(_req: Request) -> Response:
                return JSONResponse({"error": "Authorization Bearer token required"}, status_code=401)
            return Starlette(routes=[], exception_handlers={Exception: auth_error})

        token = auth_header.split(" ", 1)[1].strip()
        mode_param = (request.query_params.get("mode") or "safe").lower()
        is_unsafe = mode_param == "unsafe"

        url = request.url
        airflow_prefix = _compute_airflow_prefix(request)
        base_url = f"{url.scheme}://{url.netloc}{airflow_prefix}"

        openapi_spec = await self._ensure_openapi_spec(base_url, token)
        if openapi_spec is None:
            async def spec_error(_req: Request) -> Response:
                return JSONResponse({"error": "Failed to fetch Airflow OpenAPI spec"}, status_code=502)
            return Starlette(routes=[], exception_handlers={Exception: spec_error})

        client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

        server_name = "Airflow MCP Server (Unsafe Mode)" if is_unsafe else "Airflow MCP Server (Safe Mode)"
        allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"] if is_unsafe else ["GET"]

        # Pre-filter OpenAPI operations so Safe mode only exposes GET endpoints
        if not is_unsafe:
            paths = openapi_spec.get("paths", {})
            filtered_paths: dict[str, dict] = {}
            for path, path_item in paths.items():
                new_item: dict[str, dict] = {}
                for method, operation in path_item.items():
                    lower_method = method.lower()
                    if lower_method in {"get", "post", "put", "delete", "patch"}:
                        if method.upper() in allowed_methods:
                            new_item[lower_method] = operation
                    # keep non-operation keys only if there will be operations
                if new_item:
                    # preserve common keys like parameters if present
                    if isinstance(path_item, dict) and "parameters" in path_item:
                        new_item["parameters"] = path_item["parameters"]
                    filtered_paths[path] = new_item
            openapi_spec = {**openapi_spec, "paths": filtered_paths}
        route_maps = [RouteMap(methods=allowed_methods, mcp_type=MCPType.TOOL)]
        mcp = FastMCPOpenAPI(
            openapi_spec=openapi_spec,
            client=client,
            name=server_name,
            route_maps=route_maps,
        )

        mcp_app = mcp.http_app(path=self._path, stateless_http=True)

        return mcp_app

    async def __call__(self, scope, receive, send):
        # Normalize empty subpath from parent mount (e.g., '/mcp' -> '/')
        if not scope.get("path"):
            scope = dict(scope)
            scope["path"] = "/"

        request = Request(scope, receive=receive)
        app = await self._build_stateless_app(request)
        # Ensure FastMCP's lifespan runs for each request since the parent app won't manage it
        if hasattr(app, "router") and hasattr(app.router, "lifespan_context"):
            async with app.router.lifespan_context(app):
                await app(scope, receive, send)
        else:
            await app(scope, receive, send)


class AirflowMCPPlugin(AirflowPlugin):
    name = "airflow_mcp_plugin"

    def on_load(self, *args, **kwargs):
        pass

    @property
    def fastapi_apps(self):
        # Mount our ASGI app under /mcp so we don't intercept core Airflow routes
        stateless = StatelessMCPMount(path="/")
        return [{"app": stateless, "url_prefix": "/mcp", "name": "Airflow MCP"}]
