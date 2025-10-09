from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Literal, cast

import aiohttp
import uvicorn
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from airflow_mcp_server.config import AirflowConfig
from airflow_mcp_server.hierarchical_manager import HierarchicalToolManager
from airflow_mcp_server.resources import register_resources
from airflow_mcp_server.toolset import AirflowOpenAPIToolset


async def serve(
    config: AirflowConfig,
    static_tools: bool = False,
    resources_dir: str | None = None,
    transport: Literal["stdio", "streamable-http", "sse"] = "stdio",
    **transport_kwargs,
) -> None:
    """Start MCP server in safe mode (read-only operations)."""

    await _serve_airflow(
        config=config,
        allowed_methods={"GET"},
        mode_label="Safe Mode",
        static_tools=static_tools,
        resources_dir=resources_dir,
        transport=transport,
        transport_kwargs=transport_kwargs,
    )


async def _serve_airflow(
    *,
    config: AirflowConfig,
    allowed_methods: set[str],
    mode_label: str,
    static_tools: bool,
    resources_dir: str | None,
    transport: Literal["stdio", "streamable-http", "sse"],
    transport_kwargs: dict[str, object],
) -> None:
    if not config.base_url:
        raise ValueError("base_url is required")
    if not config.auth_token:
        raise ValueError("auth_token is required")

    session = aiohttp.ClientSession(
        base_url=config.base_url,
        headers={"Authorization": f"Bearer {config.auth_token}"},
        timeout=aiohttp.ClientTimeout(total=30),
    )

    try:
        async with session.get("/openapi.json") as response:
            response.raise_for_status()
            openapi_spec = await response.json()

        allow_mutations = any(method != "GET" for method in allowed_methods)
        toolset = AirflowOpenAPIToolset(openapi_spec, allow_mutations=allow_mutations, session=session)

        server = Server(
            name=f"Airflow MCP Server ({mode_label})",
            version="0.9.0",
            instructions="Interact with Apache Airflow's REST API via MCP tools.",
        )

        if static_tools:
            _register_static_tools(server, toolset)
        else:
            HierarchicalToolManager(server, toolset, openapi_spec, allowed_methods)

        register_resources(server, resources_dir)

        initialization = server.create_initialization_options()

        host_value = transport_kwargs.get("host", "localhost")
        host = cast(str, host_value) if isinstance(host_value, str) else "localhost"

        port_value = transport_kwargs.get("port", 3000)
        if isinstance(port_value, (int, str)):
            port = int(port_value)
        else:
            raise TypeError("port must be an int or string")

        if transport == "stdio":
            await _run_stdio(server, initialization)
        elif transport == "streamable-http":
            await _run_streamable_http(server, host=str(host), port=int(port))
        elif transport == "sse":
            await _run_sse(server, initialization, host=str(host), port=int(port))
        else:  # pragma: no cover
            raise ValueError(f"Unsupported transport '{transport}'")
    finally:
        await session.close()


def _register_static_tools(server: Server, toolset: AirflowOpenAPIToolset) -> None:
    tools = toolset.list_tools()

    @server.list_tools()
    async def _list_tools(_: types.ListToolsRequest | None = None) -> types.ListToolsResult:
        return types.ListToolsResult(tools=tools)

    @server.call_tool()
    async def _call_tool(tool_name: str, arguments: dict[str, object]):
        try:
            return await toolset.call_tool(tool_name, arguments or {})
        except ValueError as exc:
            return [types.TextContent(type="text", text=str(exc))]


async def _run_stdio(server: Server, initialization: InitializationOptions) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, initialization, stateless=False)


async def _run_streamable_http(server: Server, *, host: str, port: int) -> None:
    session_manager = StreamableHTTPSessionManager(server, stateless=False)

    class App:
        def __init__(self, manager: StreamableHTTPSessionManager) -> None:
            self._manager = manager

        async def __call__(self, scope: Any, receive: Any, send: Any):
            await self._manager.handle_request(scope, receive, send)

    @asynccontextmanager
    async def lifespan(_: Starlette):
        async with session_manager.run():
            yield

    async def root(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[
            Route("/", endpoint=root, methods=["GET"]),
            Mount("/mcp", app=App(session_manager)),
        ],
        lifespan=lifespan,
    )

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    await uvicorn.Server(config).serve()


async def _run_sse(server: Server, initialization: InitializationOptions, *, host: str, port: int) -> None:
    transport = SseServerTransport("/messages")

    async def sse(scope: Any, receive: Any, send: Any):
        async with transport.connect_sse(scope, receive, send) as (read_stream, write_stream):
            await server.run(read_stream, write_stream, initialization, stateless=True)
        return Response(status_code=204)

    async def status(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[
            Route("/", endpoint=status, methods=["GET"]),
            Route("/events", endpoint=sse, methods=["GET"]),
            Mount("/messages", app=transport.handle_post_message),
        ]
    )

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    await uvicorn.Server(config).serve()
