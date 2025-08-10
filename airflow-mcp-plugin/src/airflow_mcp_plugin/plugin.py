from __future__ import annotations

import asyncio
import logging

import httpx
from airflow.plugins_manager import AirflowPlugin
from airflow_mcp_server.config import AirflowConfig
from airflow_mcp_server.prompts import add_airflow_prompts
from airflow_mcp_server.resources import add_airflow_resources
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


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
                resp = await client.get("/openapi.json")
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
        base_url = f"{url.scheme}://{url.netloc}"

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
        route_maps = [RouteMap(methods=allowed_methods, mcp_type=MCPType.TOOL)]

        mcp = FastMCP.from_openapi(
            openapi_spec=openapi_spec,
            client=client,
            name=server_name,
            route_maps=route_maps,
        )

        config = AirflowConfig(base_url=base_url, auth_token=token)
        mode_str = "unsafe" if is_unsafe else "safe"
        add_airflow_resources(mcp, config, mode=mode_str)
        add_airflow_prompts(mcp, mode=mode_str)

        mcp_app = mcp.http_app(path=self._path, stateless_http=True)

        return mcp_app

    async def __call__(self, scope, receive, send):
        request = Request(scope, receive=receive)
        app = await self._build_stateless_app(request)
        await app(scope, receive, send)


class AirflowMCPPlugin(AirflowPlugin):
    name = "airflow_mcp_plugin"

    def on_load(self, *args, **kwargs):
        pass

    @property
    def fastapi_apps(self):
        stateless = StatelessMCPMount(path="/mcp")
        return [{"app": stateless, "url_prefix": "/", "name": "Airflow MCP"}]
