# HTTP Server API

RMCP provides a comprehensive HTTP API for web applications and remote access.

## Getting Started

### Quick Start
```bash
# Install with HTTP dependencies
pip install rmcp[http]

# Start HTTP server
rmcp serve-http

# Test the server
curl http://localhost:8000/health
```

### Using the Live Server
Try the deployed server without any installation:

- **HTTP Server**: `https://rmcp-server-394229601724.us-central1.run.app/mcp`
- **Interactive Docs**: `https://rmcp-server-394229601724.us-central1.run.app/docs`
- **Health Check**: `https://rmcp-server-394229601724.us-central1.run.app/health`

## API Endpoints

### Main MCP Endpoint

**POST /mcp**

Main Model Context Protocol communication endpoint.

**Request Headers:**
- `Content-Type: application/json`
- `MCP-Protocol-Version: 2025-06-18` (required after initialization)
- `MCP-Session-Id: <session-id>` (included automatically after initialization)

**JSON-RPC 2.0 Request Body:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "<method_name>",
  "params": {}
}
```

**Available Methods:**
- `initialize` - Initialize MCP session
- `tools/list` - List available statistical analysis tools
- `tools/call` - Execute statistical analysis tool
- `resources/list` - List available data resources
- `prompts/list` - List available prompt templates

### Server-Sent Events

**GET /mcp/sse**

Real-time event stream for progress updates and notifications.

**Response:** `text/event-stream` with JSON-encoded events:

```javascript
// Progress notification
event: notification
data: {"method": "notifications/progress", "params": {"progressToken": "abc", "progress": 50, "total": 100}}

// Keep-alive signal
event: keepalive
data: {"status": "ok"}
```

### Health Check

**GET /health**

Server health and status information.

**Response:**
```json
{
  "status": "healthy",
  "transport": "HTTP"
}
```

## Example Usage

### JavaScript Client
```javascript
// Initialize session
const initResponse = await fetch('/mcp', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
      protocolVersion: '2025-06-18',
      capabilities: {},
      clientInfo: { name: 'rmcp-client', version: '1.0.0' }
    }
  })
});

// List available tools
const toolsResponse = await fetch('/mcp', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'MCP-Protocol-Version': '2025-06-18',
    'MCP-Session-Id': sessionId
  },
  body: JSON.stringify({
    jsonrpc: '2.0',
    id: 2,
    method: 'tools/list',
    params: {}
  })
});
```

### Python Client
```python
import httpx

# Initialize session
response = httpx.post('http://localhost:8000/mcp', json={
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2025-06-18',
        'capabilities': {},
        'clientInfo': {'name': 'rmcp-client', 'version': '1.0.0'}
    }
})

session_id = response.json()['result']['sessionId']

# Call statistical tool
response = httpx.post('http://localhost:8000/mcp',
    headers={
        'MCP-Protocol-Version': '2025-06-18',
        'MCP-Session-Id': session_id
    },
    json={
        'jsonrpc': '2.0',
        'id': 2,
        'method': 'tools/call',
        'params': {
            'name': 'linear_model',
            'arguments': {
                'data': [[1, 2], [3, 4], [5, 6]],
                'formula': 'y ~ x'
            }
        }
    }
)
```

## Deployment

### Docker Deployment
```bash
# Production deployment
docker build -f docker/Dockerfile --target production -t rmcp-production .
docker run -p 8000:8000 rmcp-production rmcp serve-http
```

### Environment Configuration
```bash
# Configure via environment variables
export RMCP_HTTP_HOST=0.0.0.0
export RMCP_HTTP_PORT=8000
export RMCP_LOG_LEVEL=INFO

# Start server
rmcp serve-http
```

### Cloud Deployment
The HTTP API is designed for cloud deployment with:
- Session management for concurrent users
- CORS support for web applications
- Health checks for load balancers
- Structured logging for monitoring
