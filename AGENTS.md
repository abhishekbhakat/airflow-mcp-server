# Airflow MCP — Agent Ramp-up Guide

## Mission
The repo ships two complementary MCP deliverables that sit in front of the Airflow 3 REST API:

1. **airflow-mcp-server** – an advanced FastMCP deployment with hierarchical discovery, safe/unsafe modes, transport flexibility, and future prompt/resource hooks.
2. **airflow-mcp-plugin** – a lightweight Airflow webserver plugin that simply exposes the Airflow instance’s REST API as MCP tools at `/mcp`.

Both surfaces expose Airflow operations as MCP tools, but choose based on **runtime model**:
- **Server** runs as a separate process alongside Airflow and is suited for richer agent workflows or multi-tenant orchestration.
- **Plugin** runs in-process with Airflow and is the easiest path to add MCP access to an existing Airflow deployment without managing another service.

## High-level Architecture

### airflow-mcp-server (CLI app)
- **CLI entrypoint**: `src/airflow_mcp_server/__init__.py` exposes Click flags to select safe/unsafe mode, static vs hierarchical tooling, and transport (`stdio`, `streamable-http`, `sse`). It validates configuration via `AirflowConfig` and dispatches to the async `serve_safe` or `serve_unsafe` runners.
- **Configuration**: `AirflowConfig` (`config.py`) requires both `base_url` and `auth_token` (JWT). CLI flags may be overridden by `AIRFLOW_BASE_URL` and `AUTH_TOKEN` environment variables.
- **Server runners**: `server_safe.py` (GET-only) and `server_unsafe.py` (all methods) fetch the Airflow OpenAPI spec once at startup, build an `httpx.AsyncClient` with the caller’s JWT, attach resources/prompts placeholders, and run FastMCP on the selected transport.
- **Tool generation**:
  - *Static mode*: FastMCP autogenerates one tool per OpenAPI operation via `FastMCP.from_openapi`.
  - *Hierarchical mode*: `HierarchicalToolManager` groups operations by OpenAPI tag (“category”), keeps navigation tools (`browse_categories`, `select_category`, `get_current_category`), and mounts category-specific FastMCP sub-servers. Utilities live in `utils/category_mapper.py`.

### airflow-mcp-plugin (Airflow webserver mount)
- Mounts a stateless MCP server inside Airflow’s webserver (`airflow-mcp-plugin/src/airflow_mcp_plugin/plugin.py`).
- Each HTTP request must include `Authorization: Bearer <token>`; the plugin forwards that JWT when calling Airflow’s OpenAPI endpoints.
- `StatelessMCPMount` caches the OpenAPI spec, filters non-GET operations when `mode=safe`, and exposes tools through `FastMCPOpenAPI.http_app`.
- `_compute_airflow_prefix` handles reverse-proxy path prefixes (e.g., Astronomer deployments) before forming the API base URL.
- Designed for simplicity: no hierarchical tooling, prompts, or resources—just direct OpenAPI-derived tools for the current request context.

## Modes & Transports
- **Safe mode (`--safe`)**: exposes only GET operations; use when agents must remain read-only.
- **Unsafe mode (`--unsafe`)**: default; POST/PUT/PATCH/DELETE allowed. Agents must take care.
- **Static tools (`--static-tools`)**: skip hierarchical browsing; ideal for automated clients.
- **Hierarchical discovery (default)**: better UX for humans exploring large API surfaces.
- **Transports**:
  - `stdio` (default) for local integrations.
  - `--http` for Streamable HTTP (recommended).
  - `--sse` deprecated but still available.

## MCP Capabilities Overview
FastMCP handles capability negotiation automatically when tools are registered, but prompt/resource helpers still need implementation:

| Capability | What to declare | Key APIs |
|------------|-----------------|----------|
| Tools      | `{ "tools": { "listChanged": true? } }` | `tools/list`, `tools/call` |
| Prompts    | `{ "prompts": { "listChanged": true? } }` | `prompts/list`, `prompts/get` |
| Resources  | `{ "resources": { "subscribe": bool, "listChanged": bool } }` | `resources/list`, `resources/read`, `resources/subscribe`, `resources/templates/list` |

Reference: [ModelContextProtocol spec](https://modelcontextprotocol.io/specification/) (see snippets pulled via Context7).

## Current Gaps / Next Steps
1. **Prompts** (`prompts.py`): function stub—decide on prompt templates (e.g., “Summarize DAG”, “Diagnose failed run”) and register them with FastMCP once capability declaration is wired.
2. **Resources** (`resources.py`): stub—could expose curated Airflow docs, recent DAG run logs, or airflow.cfg excerpts. Ensure capability advertises `resources`.
3. **Hierarchical UX polish**: consider add “back_to_categories” tool (mentioned in helper text but not implemented).
4. **Testing**: pytest suite covers config, CLI, and hierarchical manager; add coverage when prompts/resources go live.

## Quick Start for Agents
**airflow-mcp-server**
1. Install via `uvx airflow-mcp-server --base-url http://airflow:8080 --auth-token <jwt>`.
2. For read-only contexts (e.g., Claude Desktop browsing), add `--safe`.
3. When interacting programmatically, use `--static-tools` to avoid dynamic discovery overhead.

**airflow-mcp-plugin**
1. `pip install "airflow-mcp-server[airflow-plugin]"` inside the Airflow deployment image/env.
2. Airflow auto-loads the plugin; MCP endpoint appears at `https://<host>/mcp`.
3. Call with `Authorization: Bearer <jwt>` and optional `?mode=unsafe` to enable writes (default is safe).

## Useful Paths
- Core CLI: `src/airflow_mcp_server/__init__.py`
- Safe server: `src/airflow_mcp_server/server_safe.py`
- Unsafe server: `src/airflow_mcp_server/server_unsafe.py`
- Hierarchical manager: `src/airflow_mcp_server/hierarchical_manager.py`
- Airflow plugin: `airflow-mcp-plugin/src/airflow_mcp_plugin/plugin.py`
- Tests: `tests/`

Keep this file updated as prompts/resources mature or if capability declarations change.
