# Airflow MCP Plugin Client Configuration Reference

The plugin exposes a **Streamable HTTP** endpoint at `http(s)://<airflow-host>/mcp`. All MCP clients must:

- Connect via HTTP (no stdio transport is available for the plugin)
- Provide the per-request header `Authorization: Bearer <access-token>`
- Optionally append `?mode=unsafe` to enable write operations

Replace `<airflow-host>` with the address of your Airflow webserver (default examples below use `http://localhost:8080`).

> Many MCP clients (Cursor, Claude Desktop, Windsurf, JetBrains, etc.) rely on the [`mcp-remote`](https://github.com/geelen/mcp-remote) helper to forward custom headers to remote servers. Examples below use that wrapper when direct header injection is not yet supported.

---

## Cursor

`~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8080/mcp",
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

## Claude Code CLI

```bash
claude mcp add --transport http airflow-plugin http://localhost:8080/mcp --header "Authorization: Bearer <access-token>"
```

## Claude Desktop

`claude_desktop_config.json`

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8080/mcp",
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

## Windsurf

`~/.windsurf/mcp.json`

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8080/mcp",
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

## VS Code / VS Code Insiders

`settings.json`

```json
"mcp": {
  "servers": {
    "airflow-mcp-plugin": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer <access-token>"
      }
    }
  }
}
```

## JetBrains IDEs / Junie

Settings → Tools → AI Assistant → Model Context Protocol:

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8080/mcp",
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

## Cline

`cline_mcp_settings.json`

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer <access-token>"
      }
    }
  }
}
```

## Zed

`settings.json`

```json
{
  "context_servers": {
    "Airflow MCP Plugin": {
      "type": "streamableHttp",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer <access-token>"
      }
    }
  }
}
```

## Copilot Coding Agent

Repository → Settings → Copilot → Coding Agent → MCP configuration:

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "type": "http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer <access-token>"
      }
    }
  }
}
```

## Gemini CLI

`~/.gemini/settings.json`

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "httpUrl": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer <access-token>",
        "Accept": "application/json, text/event-stream"
      }
    }
  }
}
```

## Warp

Settings → AI → Manage MCP servers:

```json
{
  "Airflow Plugin": {
    "url": "http://localhost:8080/mcp",
    "headers": {
      "Authorization": "Bearer <access-token>"
    }
  }
}
```

## Roo Code

`~/.roocode/mcp.json`

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "type": "streamable-http",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer <access-token>"
      }
    }
  }
}
```

## Perplexity Desktop

Settings → Connectors → Advanced:

```json
{
  "url": "http://localhost:8080/mcp",
  "headers": {
    "Authorization": "Bearer <access-token>"
  }
}
```

## Amazon Q Developer CLI

`~/.aws/amazonq/mcp.json`

```json
{
  "mcpServers": {
    "airflow-mcp-plugin": {
      "url": "http://localhost:8080/mcp",
      "headers": {
        "Authorization": "Bearer <access-token>"
      }
    }
  }
}
```

---

### Troubleshooting

- Confirm that Airflow webserver ingress permits requests to `/mcp` and forwards headers intact.
- Ensure tokens have sufficient scope for the desired Airflow API operations; otherwise calls will fail downstream.
- When running behind reverse proxies, update `http://localhost:8080` to the externally reachable URL and configure TLS as needed.
- If your MCP client does not yet support direct header configuration, proxy through `mcp-remote` (as shown in the examples above) to inject the `Authorization` header.
