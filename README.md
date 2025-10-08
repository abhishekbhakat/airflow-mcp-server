# airflow-mcp-server: An MCP Server for controlling Airflow 3

mcp-name: io.github.abhishekbhakat/airflow-mcp-server

### MCPHub Certification

This MCP server is certified by [MCPHub](https://mcphub.com/mcp-servers/abhishekbhakat/airflow-mcp-server). This certification ensures that airflow-mcp-server follows best practices for Model Context Protocol implementation.

### Find on Glama

<a href="https://glama.ai/mcp/servers/6gjq9w80xr">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/6gjq9w80xr/badge" />
</a>

## Overview
A [Model Context Protocol](https://modelcontextprotocol.io/) server for controlling Airflow via Airflow APIs.

## Demo Video

https://github.com/user-attachments/assets/f3e60fff-8680-4dd9-b08e-fa7db655a705

## Setup

### Usage with Claude Desktop

#### Stdio Transport (Default)
```json
{
    "mcpServers": {
        "airflow-mcp-server": {
            "command": "uvx",
            "args": [
                "airflow-mcp-server",
                "--base-url",
                "http://localhost:8080",
                "--auth-token",
                "<jwt_token>"
            ]
        }
    }
}
```

### Airflow 3 Plugin (Streamable HTTP at /mcp)

Install the plugin alongside the server to mount an MCP endpoint directly in the Airflow webserver:

```bash
pip install "airflow-mcp-server[airflow-plugin]"
```

- Airflow auto-loads the plugin via entry point
- Endpoint: `http(s)://<airflow-host>/mcp`
- Stateless: every request must include `Authorization: Bearer <access-token>`
- Modes (per-request): safe by default, or `?mode=unsafe` to enable write operations

#### HTTP Transport
```json
{
    "mcpServers": {
        "airflow-mcp-server-http": {
            "command": "uvx",
            "args": [
                "airflow-mcp-server",
                "--http",
                "--port",
                "3000",
                "--base-url",
                "http://localhost:8080",
                "--auth-token",
                "<jwt_token>"
            ]
        }
    }
}
```

> **Note:**
> - Set `base_url` to the root Airflow URL (e.g., `http://localhost:8080`).
> - Do **not** include `/api/v2` in the base URL. The server will automatically fetch the OpenAPI spec from `${base_url}/openapi.json`.
> - Only JWT token is required for authentication. Cookie and basic auth are no longer supported in Airflow 3.0.

### Transport Options

The server supports multiple transport protocols:

#### Stdio Transport (Default)
Standard input/output transport for direct process communication:
```bash
airflow-mcp-server --safe --base-url http://localhost:8080 --auth-token <jwt>
```

#### HTTP Transport
Uses Streamable HTTP for better scalability and web compatibility:
```bash
airflow-mcp-server --safe --http --port 3000 --base-url http://localhost:8080 --auth-token <jwt>
```

> **Note:** SSE transport is deprecated. Use `--http` for new deployments as it provides better bidirectional communication and is the recommended approach by FastMCP.

### Operation Modes

The server supports two operation modes:

- **Safe Mode** (`--safe`): Only allows read-only operations (GET requests). This is useful when you want to prevent any modifications to your Airflow instance.
- **Unsafe Mode** (`--unsafe`): Allows all operations including modifications. This is the default mode.

To start in safe mode:
```bash
airflow-mcp-server --safe
```

To explicitly start in unsafe mode (though this is default):
```bash
airflow-mcp-server --unsafe
```

### Tool Discovery Modes

The server supports two tool discovery approaches:

- **Hierarchical Discovery** (default): Tools are organized by categories (DAGs, Tasks, Connections, etc.). Browse categories first, then select specific tools. More manageable for large APIs.
- **Static Tools** (`--static-tools`): All tools available immediately. Better for programmatic access but can be overwhelming.

To use static tools:
```bash
airflow-mcp-server --static-tools
```

### Command Line Options

```bash
Usage: airflow-mcp-server [OPTIONS]

  MCP server for Airflow

Options:
  -v, --verbose      Increase verbosity
  -s, --safe         Use only read-only tools
  -u, --unsafe       Use all tools (default)
  --static-tools     Use static tools instead of hierarchical discovery
  --base-url TEXT    Airflow API base URL
  --auth-token TEXT  Authentication token (JWT)
  --http             Use HTTP (Streamable HTTP) transport instead of stdio
  --sse              Use Server-Sent Events transport (deprecated, use --http
                     instead)
  --port INTEGER     Port to run HTTP/SSE server on (default: 3000)
  --host TEXT        Host to bind HTTP/SSE server to (default: localhost)
  --help             Show this message and exit.
```

### Considerations

**Authentication**

- Only JWT authentication is supported in Airflow 3.0. You must provide a valid `AUTH_TOKEN`.

**Page Limit**

The default is 100 items, but you can change it using `maximum_page_limit` option in [api] section in the `airflow.cfg` file.

**Transport Selection**

- Use **stdio** transport for direct process communication (default)
- Use **HTTP** transport for web deployments, multiple clients, or when you need better scalability
- Avoid **SSE** transport as it's deprecated in favor of HTTP transport

## Tasks

- [x] Airflow 3 readiness
- [x] Parse OpenAPI Spec
- [x] Safe/Unsafe mode implementation
- [x] Parse proper description with list_tools.
- [x] Airflow config fetch (_specifically for page limit_)
- [x] HTTP/SSE transport support
- [ ] Env variables optional (_env variables might not be ideal for airflow plugins_)
