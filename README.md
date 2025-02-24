# airflow-mcp-server: An MCP Server for controlling Airflow

### Find on Glama

<a href="https://glama.ai/mcp/servers/6gjq9w80xr">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/6gjq9w80xr/badge" />
</a>


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
        "AIRFLOW_BASE_URL": "http://<host:port>/api/v1",
        "AUTH_TOKEN": "<base64_encoded_username_password>"
      }
    }
  }
}
```


# Scope

2 different streams in which Airflow MCP Server can be used:
- Adding Airflow to AI  (_complete access to an Airflow deployment_)
  - This will enable AI to be able to write DAGs and just do things in a schedule on its own.
  - Use command `airflow-mcp-server` or `airflow-mcp-server --unsafe`.
- Adding AI to Airflow (_read-only access using Airflow Plugin_)
  - This stream can enable Users to be able to get a better understanding about their deployment. Specially in cases where teams have hundreds, if not thousands of dags.
  - Use command `airflow-mcp-server --safe`.
