# HTTP Server API

RMCP serves the MCP **Streamable HTTP** transport (protocol `2025-11-25`,
with `2025-06-18` back-compat) via the official MCP SDK. It works with any
spec-compliant MCP client: Claude custom connectors, the Claude API MCP
connector, OpenAI's Responses API / ChatGPT remote MCP support, and the
official `mcp` client SDKs.

## Getting Started

### Quick Start
```bash
pip install rmcp

# Start HTTP server (localhost, no auth required)
rmcp serve-http

# Test the server
curl http://localhost:8000/health
```

### Using the Live Server

- **MCP Endpoint**: `https://rmcp-server-394229601724.us-central1.run.app/mcp`
- **Health Check**: `https://rmcp-server-394229601724.us-central1.run.app/health`

## Authentication

Remote binds require a bearer token. Configure accepted keys with the
`RMCP_API_KEY` environment variable (comma-separated for multiple keys) or
repeatable `--api-key` flags:

```bash
RMCP_API_KEY=your-secret rmcp serve-http --host 0.0.0.0 --port 8080
```

Clients send the token in the `Authorization` header:

```
Authorization: Bearer your-secret
```

`/health` stays open. Binding to a non-localhost address without a key is
refused unless you pass `--allow-unauthenticated`.

## API Endpoints

### MCP Endpoint (Streamable HTTP)

**POST /mcp** — JSON-RPC 2.0 requests. Responses arrive as JSON or an SSE
stream, depending on request type and negotiation.

**Request Headers:**
- `Content-Type: application/json`
- `Accept: application/json, text/event-stream` (required)
- `Authorization: Bearer <token>` (when auth is enabled)
- `Mcp-Session-Id: <session-id>` (returned by `initialize`; required on
  subsequent requests)
- `MCP-Protocol-Version: 2025-11-25` (recommended after initialization)

**GET /mcp** — optional server-to-client SSE stream for notifications.

**DELETE /mcp** — terminate the session.

**Handshake:** `initialize` → read the `Mcp-Session-Id` response header →
send a `notifications/initialized` notification → issue requests.

**Available methods:** `initialize`, `tools/list`, `tools/call`,
`resources/list`, `resources/templates/list`, `resources/read`,
`resources/subscribe`, `prompts/list`, `prompts/get`, `logging/setLevel`.

### Health Check

**GET /health**

```json
{
  "status": "healthy",
  "server": "RMCP MCP Server",
  "version": "0.9.0",
  "transport": "streamable-http",
  "tools": 52
}
```

## Example Usage

### Official MCP Python client

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    headers = {"Authorization": "Bearer your-secret"}  # if auth is enabled
    async with streamablehttp_client(
        "http://localhost:8000/mcp", headers=headers
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool(
                "linear_model",
                {
                    "formula": "y ~ x",
                    "data": {"y": [2.0, 4.1, 6.2], "x": [1, 2, 3]},
                },
            )
            print(result.structuredContent)
```

### Claude API (MCP connector)

```python
import anthropic

client = anthropic.Anthropic()
response = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    betas=["mcp-client-2025-11-20"],
    mcp_servers=[{
        "type": "url",
        "url": "https://your-server.example.com/mcp",
        "name": "rmcp-statistics",
        "authorization_token": "your-secret",
    }],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "rmcp-statistics"}],
    messages=[{"role": "user", "content": "Run a linear regression of sales on marketing."}],
)
```

### OpenAI Responses API

```python
from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model="gpt-5",
    tools=[{
        "type": "mcp",
        "server_label": "rmcp-statistics",
        "server_url": "https://your-server.example.com/mcp",
        "headers": {"Authorization": "Bearer your-secret"},
    }],
    input="Run a linear regression of sales on marketing.",
)
```

## Deployment

### Docker Deployment
```bash
docker build --target production -t rmcp-production .
docker run -p 8000:8000 -e RMCP_API_KEY=your-secret \
  rmcp-production rmcp serve-http --host 0.0.0.0
```

### Environment Configuration
```bash
export RMCP_HTTP_HOST=0.0.0.0
export RMCP_HTTP_PORT=8000
export RMCP_API_KEY=your-secret
export RMCP_LOG_LEVEL=INFO

rmcp serve-http
```

### HTTPS
```bash
rmcp serve-http --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### Cloud Deployment
The HTTP API is designed for cloud deployment with:
- Spec-compliant Streamable HTTP session management
- Bearer-token authentication for remote access
- CORS support for web applications
- Health checks for load balancers
- Structured logging for monitoring
