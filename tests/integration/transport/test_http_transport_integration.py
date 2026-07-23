"""
Integration tests for the Streamable HTTP transport (SDK-based).

Exercises the full server (all built-in tools registered) through the
spec-compliant Streamable HTTP endpoint:
- initialize handshake and protocol version negotiation
- tools/list and tools/call (R execution where available)
- JSON-RPC error handling for invalid payloads
- SSE response framing, health check, and CORS
"""

import pytest

httpx = pytest.importorskip("httpx", reason="httpx not available")

from rmcp.cli import _register_builtin_tools  # noqa: E402
from rmcp.core.server import create_server  # noqa: E402
from rmcp.registries.prompts import (  # noqa: E402
    register_prompt_functions,
    statistical_workflow_prompt,
)
from rmcp.transport.sdk import create_streamable_http_app  # noqa: E402

from tests.utils import (  # noqa: E402
    extract_json_content,
    initialize_streamable_session,
    parse_streamable_response,
    streamable_http_client,
)


@pytest.fixture
def full_app(tmp_path):
    """Streamable HTTP app with all built-in RMCP tools registered."""
    server = create_server()
    server.configure(allowed_paths=[str(tmp_path)], read_only=True)
    _register_builtin_tools(server)
    register_prompt_functions(server.prompts, statistical_workflow_prompt)
    return create_streamable_http_app(server, manage_server_lifecycle=False)


class TestStreamableHTTPMCPCompliance:
    async def test_initialize_request(self, full_app):
        async with streamable_http_client(full_app) as client:
            result, headers = await initialize_streamable_session(client)
            assert result["protocolVersion"] == "2025-11-25"
            assert result["serverInfo"]["name"] == "RMCP MCP Server"
            assert "tools" in result["capabilities"]
            assert "Mcp-Session-Id" in headers

    async def test_protocol_version_negotiation(self, full_app):
        async with streamable_http_client(full_app) as client:
            result, _ = await initialize_streamable_session(
                client, protocol_version="2025-06-18"
            )
            assert result["protocolVersion"] == "2025-06-18"

    async def test_tools_list_request(self, full_app):
        async with streamable_http_client(full_app) as client:
            _, headers = await initialize_streamable_session(client)
            response = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                headers=headers,
            )
            message = parse_streamable_response(response)
            tools = message["result"]["tools"]
            names = {tool["name"] for tool in tools}
            assert {"linear_model", "load_example", "summary_stats"} <= names
            linear_model = next(t for t in tools if t["name"] == "linear_model")
            assert "inputSchema" in linear_model
            assert "outputSchema" in linear_model

    @pytest.mark.local
    async def test_tool_call_request(self, full_app):
        """Real R execution through the Streamable HTTP endpoint."""
        async with streamable_http_client(full_app) as client:
            _, headers = await initialize_streamable_session(client)
            response = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "load_example",
                        "arguments": {"dataset_name": "sales"},
                    },
                },
                headers=headers,
                timeout=60.0,
            )
            message = parse_streamable_response(response)
            assert "result" in message, message
            payload = extract_json_content(message)
            assert payload


class TestStreamableHTTPErrorHandling:
    async def test_invalid_json_request(self, full_app):
        async with streamable_http_client(full_app) as client:
            _, headers = await initialize_streamable_session(client)
            response = await client.post("/mcp", content=b"{not json", headers=headers)
            assert response.status_code == 400

    async def test_unknown_method(self, full_app):
        async with streamable_http_client(full_app) as client:
            _, headers = await initialize_streamable_session(client)
            response = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 4, "method": "definitely/not_a_method"},
                headers=headers,
            )
            message = parse_streamable_response(response)
            assert "error" in message
            # SDK reports unrecognized methods as a request validation error
            assert message["error"]["code"] in (-32600, -32601, -32602)

    async def test_unknown_tool_returns_tool_error(self, full_app):
        async with streamable_http_client(full_app) as client:
            _, headers = await initialize_streamable_session(client)
            response = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "no_such_tool", "arguments": {}},
                },
                headers=headers,
            )
            message = parse_streamable_response(response)
            # Unknown tool surfaces as a JSON-RPC error or isError result
            assert "error" in message or message["result"].get("isError")


class TestStreamableHTTPFraming:
    async def test_post_returns_sse_stream(self, full_app):
        """Responses are SSE-framed per the Streamable HTTP spec."""
        async with streamable_http_client(full_app) as client:
            _, headers = await initialize_streamable_session(client)
            response = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 6, "method": "prompts/list"},
                headers=headers,
            )
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            message = parse_streamable_response(response)
            prompt_names = [p["name"] for p in message["result"]["prompts"]]
            assert "statistical_workflow" in prompt_names


class TestStreamableHTTPHealthCheck:
    async def test_health_check_endpoint(self, full_app):
        async with streamable_http_client(full_app) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "healthy"
            assert body["tools"] > 40


class TestStreamableHTTPCORS:
    async def test_cors_headers(self, full_app):
        async with streamable_http_client(full_app) as client:
            response = await client.options(
                "/mcp",
                headers={
                    "Origin": "https://claude.ai",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,mcp-session-id",
                },
            )
            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers
