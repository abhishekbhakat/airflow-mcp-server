# airflow-mcp-server: An MCP Server for controlling Airflow


## Overview
A Model Context Protocol server for controlling Airflow via Airflow APIs.

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
        "OPENAPI_SPEC": "<path_to_spec.yaml>",
        "AIRFLOW_BASE_URL": "http://<host:port>/api/v1",
        "AUTH_TOKEN": "<base64_encoded_username_password>"
      }
    }
  }
}
```
