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

Config:

```json
{
  "mcpServers": {
    "airflow-mcp-server": {
      "type": "sse",
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```
Use (stateless):
- Endpoint: `http(s)://<airflow-host>/mcp`
- Every request must include header: `Authorization: Bearer <access-token>`
- The token is forwarded per-request to Airflow APIs (no shared auth state)
- Mode per-request:
  - Safe (default): `http(s)://<airflow-host>/mcp`
  - Unsafe: `http(s)://<airflow-host>/mcp?mode=unsafe` (enables POST/PUT/DELETE/PATCH)
  - Streamable HTTP (stateless)
