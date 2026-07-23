"""Unit tests for the Streamable HTTP transport (SDK-based)."""

import pytest

httpx = pytest.importorskip("httpx", reason="httpx not available")

from rmcp.core.server import create_server  # noqa: E402
from rmcp.transport.sdk import (  # noqa: E402
    BearerAuthMiddleware,
    create_streamable_http_app,
)

from tests.utils import (  # noqa: E402
    initialize_streamable_session,
    parse_streamable_response,
    streamable_http_client,
)


def _make_server(tmp_path):
    server = create_server()
    server.configure(allowed_paths=[str(tmp_path)], read_only=True)

    async def ping_handler(context, params):
        return {"pong": True}

    server.tools.register(
        name="ping",
        handler=ping_handler,
        input_schema={"type": "object", "properties": {}},
        description="Ping",
    )
    return server


def _make_app(tmp_path, **kwargs):
    kwargs.setdefault("manage_server_lifecycle", False)
    return create_streamable_http_app(_make_server(tmp_path), **kwargs)


class TestHealthEndpoint:
    async def test_health_open_without_auth(self, tmp_path):
        app = _make_app(tmp_path, api_keys={"secret"})
        async with streamable_http_client(app) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "healthy"
            assert body["transport"] == "streamable-http"
            assert body["tools"] == 1


class TestBearerAuth:
    async def test_mcp_requires_token_when_keys_configured(self, tmp_path):
        app = _make_app(tmp_path, api_keys={"secret"})
        async with streamable_http_client(app) as client:
            response = await client.post("/mcp", json={})
            assert response.status_code == 401
            assert response.headers["WWW-Authenticate"] == "Bearer"

    async def test_wrong_token_rejected(self, tmp_path):
        app = _make_app(tmp_path, api_keys={"secret"})
        async with streamable_http_client(
            app, headers={"Authorization": "Bearer wrong"}
        ) as client:
            response = await client.post("/mcp", json={})
            assert response.status_code == 401

    async def test_valid_token_accepted(self, tmp_path):
        app = _make_app(tmp_path, api_keys={"secret"})
        async with streamable_http_client(
            app, headers={"Authorization": "Bearer secret"}
        ) as client:
            result, _ = await initialize_streamable_session(client)
            assert result["protocolVersion"]

    async def test_no_keys_means_open(self, tmp_path):
        app = _make_app(tmp_path)
        async with streamable_http_client(app) as client:
            result, _ = await initialize_streamable_session(client)
            assert result["serverInfo"]["name"] == "RMCP MCP Server"

    async def test_middleware_ignores_non_mcp_paths(self):
        async def inner_app(scope, receive, send):
            from starlette.responses import PlainTextResponse

            await PlainTextResponse("ok")(scope, receive, send)

        middleware = BearerAuthMiddleware(inner_app, api_keys={"secret"})
        app_client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=middleware),
            base_url="http://testserver",
        )
        async with app_client:
            assert (await app_client.get("/health")).status_code == 200
            assert (await app_client.get("/mcp")).status_code == 401


class TestStreamableHTTPProtocol:
    async def test_initialize_negotiates_protocol(self, tmp_path):
        app = _make_app(tmp_path)
        async with streamable_http_client(app) as client:
            result, headers = await initialize_streamable_session(client)
            assert result["protocolVersion"] in ("2025-11-25", "2025-06-18")
            assert "Mcp-Session-Id" in headers

    async def test_tools_list_and_call(self, tmp_path):
        app = _make_app(tmp_path)
        async with streamable_http_client(app) as client:
            _, headers = await initialize_streamable_session(client)
            response = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                headers=headers,
            )
            message = parse_streamable_response(response)
            tool_names = [tool["name"] for tool in message["result"]["tools"]]
            assert "ping" in tool_names

            response = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "ping", "arguments": {}},
                },
                headers=headers,
            )
            message = parse_streamable_response(response)
            assert message["result"]["structuredContent"] == {"pong": True}

    async def test_request_without_session_rejected(self, tmp_path):
        app = _make_app(tmp_path)
        async with streamable_http_client(app) as client:
            await initialize_streamable_session(client)
            response = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "id": 9, "method": "tools/list"},
            )
            assert response.status_code == 400

    async def test_session_delete_terminates(self, tmp_path):
        app = _make_app(tmp_path)
        async with streamable_http_client(app) as client:
            _, headers = await initialize_streamable_session(client)
            if not headers:
                pytest.skip("stateless server: no session to terminate")
            response = await client.delete("/mcp", headers=headers)
            assert response.status_code in (200, 204)

    async def test_cors_preflight(self, tmp_path):
        app = _make_app(tmp_path)
        async with streamable_http_client(app) as client:
            response = await client.options(
                "/mcp",
                headers={
                    "Origin": "https://claude.ai",
                    "Access-Control-Request-Method": "POST",
                },
            )
            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers
