# Airflow MCP Client Configuration Reference

This document aggregates MCP client configuration snippets modelled after the Context7 examples. Every section shows a **stdio-first** setup and, where supported, an **HTTP transport** alternative using the streamable HTTP endpoint exposed by `airflow-mcp-server`.

## Prerequisites

- Airflow 3 instance reachable at `http://localhost:8080` (adjust to your environment)
- JWT auth token with the desired Airflow permissions
- [`uv`](https://github.com/astral-sh/uv) installed for launching the server via `uvx`

## Launch Commands

Start the MCP server in stdio mode (ideal when the client spawns the process):

```bash
uvx airflow-mcp-server --base-url http://localhost:8080 --auth-token <jwt_token>
```

Start the server in HTTP mode before connecting remote-capable clients:

```bash
uvx airflow-mcp-server --http --port 3000 --base-url http://localhost:8080 --auth-token <jwt_token>
```

The HTTP examples assume the server is available at `http://127.0.0.1:3000/mcp`.

---

## Cursor

### Stdio

`~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "server": {
        "url": "http://127.0.0.1:3000/mcp"
      }
    }
  }
}
```

> Cursor’s remote configuration nests connection details under a `server` key; omit the older `type` field which is no longer recognized.

---

## Claude Code

### Stdio

```bash
claude mcp add airflow -- uvx airflow-mcp-server --base-url http://localhost:8080 --auth-token <jwt_token>
```

### HTTP

```bash
claude mcp add --transport http airflow http://127.0.0.1:3000/mcp
```

---

## Amp

### Stdio

```bash
amp mcp add airflow --command uvx --args "airflow-mcp-server" "--base-url" "http://localhost:8080" "--auth-token" "<jwt_token>"
```

### HTTP

```bash
amp mcp add airflow http://127.0.0.1:3000/mcp
```

---

## Windsurf

### Stdio

`~/.windsurf/mcp.json`

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "serverUrl": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## VS Code / VS Code Insiders

### Stdio

`settings.json`

```json
"mcp": {
  "servers": {
    "airflow": {
      "type": "stdio",
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

### HTTP

```json
"mcp": {
  "servers": {
    "airflow": {
      "type": "http",
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Cline

### Stdio

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Zed

### Stdio

`settings.json`

```json
{
  "context_servers": {
    "Airflow MCP": {
      "source": "custom",
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

### HTTP

```json
{
  "context_servers": {
    "Airflow MCP": {
      "source": "remote",
      "serverUrl": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Augment Code

### Stdio (UI command)

```
npx -y airflow-mcp-server --base-url http://localhost:8080 --auth-token <jwt_token>
```

or `settings.json` entry:

```json
"augment.advanced": {
  "mcpServers": [
    {
      "name": "airflow",
      "command": "uvx",
      "args": [
        "airflow-mcp-server",
        "--base-url",
        "http://localhost:8080",
        "--auth-token",
        "<jwt_token>"
      ]
    }
  ]
}
```

### HTTP

Augment currently relies on command-launch configurations. Run the HTTP server separately and use stdio until native HTTP support is available.

---

## Roo Code

### Stdio

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "type": "streamable-http",
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Gemini CLI

### Stdio

`~/.gemini/settings.json`

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "httpUrl": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Claude Desktop

### Stdio

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

Within Settings → Connectors:

```json
{
  "name": "Airflow MCP",
  "url": "http://127.0.0.1:3000/mcp"
}
```

---

## Opencode

### Stdio

```json
{
  "mcp": {
    "airflow": {
      "type": "local",
      "command": [
        "uvx",
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

### HTTP

```json
{
  "mcp": {
    "airflow": {
      "type": "remote",
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## JetBrains IDEs / Junie

### Stdio

Settings → Tools → AI Assistant → Model Context Protocol:

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "url": "http://127.0.0.1:3000/mcp",
      "type": "http"
    }
  }
}
```

---

## Kiro

### Stdio

```json
{
  "mcpServers": {
    "Airflow MCP": {
      "command": "uvx",
      "args": [
        "airflow-mcp-server",
        "--base-url",
        "http://localhost:8080",
        "--auth-token",
        "<jwt_token>"
      ],
      "autoApprove": []
    }
  }
}
```

### HTTP

```json
{
  "mcpServers": {
    "Airflow MCP": {
      "url": "http://127.0.0.1:3000/mcp",
      "type": "http"
    }
  }
}
```

---

## Trae

### Stdio

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Bun

### Stdio

```json
{
  "mcpServers": {
    "airflow": {
      "command": "bunx",
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

### HTTP

Use Bun to launch the HTTP server:

```bash
bunx airflow-mcp-server --http --port 3000 --base-url http://localhost:8080 --auth-token <jwt_token>
```

---

## Deno

### Stdio

```json
{
  "mcpServers": {
    "airflow": {
      "command": "deno",
      "args": [
        "run",
        "--allow-env",
        "--allow-net",
        "npm:airflow-mcp-server",
        "--base-url",
        "http://localhost:8080",
        "--auth-token",
        "<jwt_token>"
      ]
    }
  }
}
```

### HTTP

```bash
deno run --allow-env --allow-net npm:airflow-mcp-server --http --port 3000 --base-url http://localhost:8080 --auth-token <jwt_token>
```

---

## Docker

### Stdio

Run interactively:

```bash
docker run -i --rm ghcr.io/abhishekbhakat/airflow-mcp-server --base-url http://host.docker.internal:8080 --auth-token <jwt_token>
```

### HTTP

```bash
docker run -i --rm -p 3000:3000 ghcr.io/abhishekbhakat/airflow-mcp-server --http --port 3000 --base-url http://host.docker.internal:8080 --auth-token <jwt_token>
```

---

## MCP Bundles (.mcpb)

### Stdio

Include in bundle manifest:

```json
{
  "command": "uvx",
  "args": [
    "airflow-mcp-server",
    "--base-url",
    "http://localhost:8080",
    "--auth-token",
    "<jwt_token>"
  ]
}
```

### HTTP

Reference the HTTP endpoint in the bundle metadata if supported by the client.

---

## Windows Notes

### Stdio

```json
{
  "mcpServers": {
    "airflow": {
      "command": "cmd",
      "args": [
        "/c",
        "uvx",
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Amazon Q Developer CLI

### Stdio

`~/.aws/amazonq/mcp.json`

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Warp

### Stdio

Settings → AI → Manage MCP servers:

```json
{
  "Airflow": {
    "command": "uvx",
    "args": [
      "airflow-mcp-server",
      "--base-url",
      "http://localhost:8080",
      "--auth-token",
      "<jwt_token>"
    ],
    "start_on_launch": true
  }
}
```

### HTTP

```json
{
  "Airflow": {
    "url": "http://127.0.0.1:3000/mcp"
  }
}
```

---

## Copilot Coding Agent

### Stdio

Repository → Settings → Copilot → Coding Agent → MCP configuration:

```json
{
  "mcpServers": {
    "airflow": {
      "type": "stdio",
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "type": "http",
      "url": "http://127.0.0.1:3000/mcp",
      "tools": ["tools/list", "tools/call"]
    }
  }
}
```

---

## LM Studio

### Stdio

`mcp.json`

```json
{
  "mcpServers": {
    "Airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "Airflow": {
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Visual Studio 2022

### Stdio

`mcp.json`

```json
{
  "inputs": [],
  "servers": {
    "airflow": {
      "type": "stdio",
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

### HTTP

```json
{
  "inputs": [],
  "servers": {
    "airflow": {
      "type": "http",
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Crush

### Stdio

`crush.json`

```json
{
  "$schema": "https://charm.land/crush.json",
  "mcp": {
    "airflow": {
      "type": "stdio",
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

### HTTP

```json
{
  "$schema": "https://charm.land/crush.json",
  "mcp": {
    "airflow": {
      "type": "http",
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## BoltAI

### Stdio

Settings → Plugins:

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Rovo Dev CLI

### Stdio

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Zencoder

### Stdio

```json
{
  "command": "uvx",
  "args": [
    "airflow-mcp-server",
    "--base-url",
    "http://localhost:8080",
    "--auth-token",
    "<jwt_token>"
  ]
}
```

### HTTP

Configure the MCP entry to use the remote server:

```json
{
  "url": "http://127.0.0.1:3000/mcp"
}
```

---

## Qodo Gen

### Stdio

```json
{
  "mcpServers": {
    "airflow": {
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

### HTTP

```json
{
  "mcpServers": {
    "airflow": {
      "url": "http://127.0.0.1:3000/mcp"
    }
  }
}
```

---

## Perplexity Desktop

### Stdio

Settings → Connectors → Advanced:

```json
{
  "command": "uvx",
  "args": [
    "airflow-mcp-server",
    "--base-url",
    "http://localhost:8080",
    "--auth-token",
    "<jwt_token>"
  ]
}
```

### HTTP

Perplexity Desktop currently expects command-based integrations. Run the server in HTTP mode separately; remote configuration will appear once direct URL support is available.

---

## Troubleshooting

- If a client requires explicit environment variables, set `AIRFLOW_BASE_URL` and `AUTH_TOKEN` instead of CLI flags.
- Some Windows environments need fully qualified paths to `uvx` or Python. Adjust commands accordingly.
- For remote HTTP access from another machine, replace `127.0.0.1` with the bound host/IP and ensure the port is exposed.
