# airflow-mcp-server: An MCP Server for controlling Airflow


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
        "AUTH_TOKEN": "<base64_encoded_username_password>"
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
- `AUTH_TOKEN`: The token to use for authorization (_This should be base64 encoded username:password_)
- `OPENAPI_SPEC`: The path to the OpenAPI spec file (_Optional_) (_defaults to latest stable release_)

*Currently, only Basic Auth is supported.*

**Page Limit**

The default is 100 items, but you can change it using `maximum_page_limit` option in [api] section in the `airflow.cfg` file.

## Tasks

- [x] First API
- [x] Parse OpenAPI Spec
- [x] Safe/Unsafe mode implementation
- [ ] Parse proper description with list_tools.
- [ ] Airflow config fetch (_specifically for page limit_)
- [ ] Env variables optional (_env variables might not be ideal for airflow plugins_)
