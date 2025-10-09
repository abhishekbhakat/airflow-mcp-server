# airflow-mcp-plugin

Airflow 3 plugin that mounts `airflow-mcp-server` as a Streamable HTTP endpoint at `/mcp` on the Airflow API server.

Requirements:
- Apache Airflow >= 3.0 (FastAPI backend)
- Python >= 3.10

Install (recommended via main package extra):
```bash
pip install "airflow-mcp-server[airflow-plugin]"
```

Or install the plugin directly:
```bash
pip install airflow-mcp-plugin
```

Deploy:
- Install into the Airflow webserver container environment (Docker/Compose/Helm)
- Restart the webserver; Airflow auto-loads the plugin via entry point

Use (stateless):
- Endpoint: `http(s)://<airflow-host>/mcp`
- Every request must include header: `Authorization: Bearer <access-token>`
- The token is forwarded per-request to Airflow APIs (no shared auth state)
- Mode per-request:
  - Safe (default): `http(s)://<airflow-host>/mcp`
  - Unsafe: `http(s)://<airflow-host>/mcp/?mode=unsafe` (enables POST/PUT/DELETE/PATCH)
  - Streamable HTTP (stateless)

### Usage with Claude Desktop

Claude Desktop requires a helper wrapper to forward headers. Add the plugin endpoint via [`mcp-remote`](https://github.com/geelen/mcp-remote) inside `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "Authorization:${MCP_AIRFLOW_TOKEN}"
      ],
      "env": {
        "MCP_AIRFLOW_TOKEN": "Bearer <access-token>"
      }
    }
  }
}
```

See [`CONFIG.md`](CONFIG.md) for additional MCP client configuration examples. All clients must supply the `Authorization: Bearer <token>` header and connect over HTTP.

### Usage with VS Code

Add the server definition to your `settings.json` under the `mcp.servers` block:

```json
"mcp": {
  "servers": {
    "airflow-mcp-plugin": {
      "type": "http",
      "url": "http://localhost:8080/mcp/",
      "headers": {
        "Authorization": "Bearer <access-token>"
      }
    }
  }
}
```

This configuration uses VS Code's native HTTP transport with per-request `Authorization` headers; update the URL if your Airflow instance is hosted elsewhere.
