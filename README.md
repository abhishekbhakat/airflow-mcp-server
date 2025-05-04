# airflow-mcp-server: An MCP Server for controlling Airflow

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

> **Note:**
> - Set `base_url` to the root Airflow URL (e.g., `http://localhost:8080`).
> - Do **not** include `/api/v2` in the base URL. The server will automatically fetch the OpenAPI spec from `${base_url}/openapi.json`.
> - Only JWT token is required for authentication. Cookie and basic auth are no longer supported in Airflow 3.0.

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

### Considerations

**Authentication**

- Only JWT authentication is supported in Airflow 3.0. You must provide a valid `AUTH_TOKEN`.

**Page Limit**

The default is 100 items, but you can change it using `maximum_page_limit` option in [api] section in the `airflow.cfg` file.

## Tasks

- [x] Airflow 3 readiness
- [x] Parse OpenAPI Spec
- [x] Safe/Unsafe mode implementation
- [x] Parse proper description with list_tools.
- [x] Airflow config fetch (_specifically for page limit_)
- [ ] Env variables optional (_env variables might not be ideal for airflow plugins_)
