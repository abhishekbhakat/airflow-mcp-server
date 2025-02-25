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
        "airflow-mcp-server"
      ],
      "env": {
        "AIRFLOW_BASE_URL": "http://<host:port>/api/v1",
        // Either use AUTH_TOKEN for basic auth
        "AUTH_TOKEN": "<base64_encoded_username_password>",
        // Or use COOKIE for cookie-based auth
        "COOKIE": "<session_cookie>"
      }
    }
  }
}
```

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

The MCP Server expects environment variables to be set:
- `AIRFLOW_BASE_URL`: The base URL of the Airflow API
- `AUTH_TOKEN`: The token to use for basic auth (_This should be base64 encoded username:password_) (_Optional if COOKIE is provided_)
- `COOKIE`: The session cookie to use for authentication (_Optional if AUTH_TOKEN is provided_)
- `OPENAPI_SPEC`: The path to the OpenAPI spec file (_Optional_) (_defaults to latest stable release_)

**Authentication**

The server supports two authentication methods:
- **Basic Auth**: Using base64 encoded username:password via `AUTH_TOKEN` environment variable
- **Cookie**: Using session cookie via `COOKIE` environment variable

At least one of these authentication methods must be provided.

**Page Limit**

The default is 100 items, but you can change it using `maximum_page_limit` option in [api] section in the `airflow.cfg` file.

## Tasks

- [x] First API
- [x] Parse OpenAPI Spec
- [x] Safe/Unsafe mode implementation
- [x] Allow session auth
- [ ] Parse proper description with list_tools.
- [ ] Airflow config fetch (_specifically for page limit_)
- [ ] Env variables optional (_env variables might not be ideal for airflow plugins_)
