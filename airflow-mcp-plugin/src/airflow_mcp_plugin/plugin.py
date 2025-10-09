from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import anyio
from airflow.plugins_manager import AirflowPlugin  # type: ignore[import-not-found]
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.requests import Request
from starlette.responses import JSONResponse

from airflow_mcp_plugin.toolset import AirflowOpenAPIToolset

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
    def __init__(self) -> None:
        self._openapi_spec: dict[str, Any] | None = None
        self._spec_lock = asyncio.Lock()
        self._toolsets: dict[bool, AirflowOpenAPIToolset] = {}

    async def _ensure_openapi_spec(self, base_url: str, token: str) -> dict[str, Any] | None:
        if self._openapi_spec is not None:
            return self._openapi_spec

        async with self._spec_lock:
            if self._openapi_spec is not None:
                return self._openapi_spec

            timeout = aiohttp.ClientTimeout(total=30)
            headers = {"Authorization": f"Bearer {token}"}
            try:
                async with aiohttp.ClientSession(base_url=base_url, headers=headers, timeout=timeout) as session:
                    async with session.get("openapi.json") as response:
                        response.raise_for_status()
                        self._openapi_spec = await response.json()
                        return self._openapi_spec
            except Exception as exc:
                logger.error("Failed to fetch OpenAPI spec: %s", exc)
                return None

    def _get_toolset(self, spec: dict[str, Any], allow_mutations: bool) -> AirflowOpenAPIToolset:
        key = allow_mutations
        if key not in self._toolsets:
            self._toolsets[key] = AirflowOpenAPIToolset(spec, allow_mutations)
        return self._toolsets[key]

    def _build_server(self, toolset: AirflowOpenAPIToolset, base_url: str, token: str) -> Server:
        server = Server(name="Airflow MCP Plugin", version="0.2.0")

        @server.list_tools()
        async def _list_tools(_: types.ListToolsRequest | None = None):
            return toolset.list_tools()

        @server.call_tool()
        async def _call_tool(tool_name: str, arguments: dict[str, Any]):
            return await toolset.call_tool(tool_name, arguments or {}, base_url, token)

        return server

    async def __call__(self, scope, receive, send):
        if scope.get("path") in {None, ""}:
            scope = dict(scope)
            scope["path"] = "/"

        request = Request(scope, receive=receive)

        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            response = JSONResponse({"error": "Authorization Bearer token required"}, status_code=401)
            await response(scope, receive, send)
            return

        token = auth_header.split(" ", 1)[1].strip()
        mode_param = (request.query_params.get("mode") or "safe").lower()
        allow_mutations = mode_param == "unsafe"

        url = request.url
        airflow_prefix = _compute_airflow_prefix(request)
        base_url = f"{url.scheme}://{url.netloc}{airflow_prefix}"

        spec = await self._ensure_openapi_spec(base_url, token)
        if spec is None:
            response = JSONResponse({"error": "Failed to fetch Airflow OpenAPI spec"}, status_code=502)
            await response(scope, receive, send)
            return

        toolset = self._get_toolset(spec, allow_mutations)
        server = self._build_server(toolset, base_url, token)
        transport = StreamableHTTPServerTransport(mcp_session_id=None)
        initialization = server.create_initialization_options()

        async with transport.connect() as (read_stream, write_stream):
            async with anyio.create_task_group() as task_group:
                task_group.start_soon(
                    server.run,
                    read_stream,
                    write_stream,
                    initialization,
                    False,
                    True,
                )
                try:
                    await transport.handle_request(scope, receive, send)
                finally:
                    task_group.cancel_scope.cancel()


class AirflowMCPPlugin(AirflowPlugin):
    name = "airflow_mcp_plugin"

    fastapi_apps = [{"app": StatelessMCPMount(), "url_prefix": "/mcp", "name": "Airflow MCP"}]
