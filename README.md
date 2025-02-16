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

> You can download the openapi spec from [Airflow REST API](https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html)

# Scope

2 different streams in which Airflow MCP Server can be used:
- Adding Airflow to AI  (_complete access to an Airflow deployment_)
  - This will enable AI to be able to write DAGs and just do things in a schedule on its own.
- Adding AI to Airflow (_read-only access using Airflow Plugin_)
  - This stream can enable Users to be able to get a better understanding about their deployment. Specially in cases where teams have hundreds, if not thousands of dags.
