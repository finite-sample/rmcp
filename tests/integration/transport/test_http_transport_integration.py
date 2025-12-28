"""
Integration tests for HTTP transport.
Tests the complete HTTP transport functionality in a real server environment:
- Actual HTTP server startup and requests
- JSON-RPC protocol compliance
- Server-Sent Events streaming
- Error handling in real scenarios
- Performance and concurrency
"""

import asyncio
import json
import time

import pytest

# Skip tests if FastAPI not available
fastapi = pytest.importorskip("fastapi", reason="FastAPI not available")
httpx = pytest.importorskip("httpx", reason="httpx not available")
from rmcp.core.server import create_server  # noqa: E402
from rmcp.transport.http import HTTPTransport  # noqa: E402


@pytest.fixture
async def http_server_with_tools():
    """Create an HTTP server with all RMCP tools registered."""
    from rmcp.cli import _register_builtin_tools

    # Create server and register tools
    server = create_server()
    _register_builtin_tools(server)
    # Create HTTP transport
    transport = HTTPTransport(
        host="127.0.0.1", port=0
    )  # Use port 0 for auto-assignment
    transport.set_message_handler(server.create_message_handler(transport))
    # Start server in background
    server_task = None
    try:
        # Start the server
        await transport.startup()
        # Get the actual port assigned
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        # Update transport with actual port
        transport.port = port
        # Run server in background
        server_task = asyncio.create_task(transport.run())
        # Wait a bit for server to start
        await asyncio.sleep(0.1)
        yield transport
    finally:
        if server_task:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
        await transport.shutdown()


class TestHTTPTransportMCPCompliance:
    """Test MCP protocol compliance over HTTP."""

    @pytest.mark.asyncio
    async def test_initialize_request(self):
        """Test MCP initialize request over HTTP."""
        transport = HTTPTransport(host="127.0.0.1", port=8001)
        server = create_server()
        transport.set_message_handler(server.create_message_handler(transport))
        # Start server in background for short test
        server_task = asyncio.create_task(transport.run())
        await asyncio.sleep(0.1)  # Let server start
        try:
            async with httpx.AsyncClient() as client:
                # Send initialize request
                initialize_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"},
                    },
                }
                response = await client.post(
                    f"http://127.0.0.1:{transport.port}/mcp",
                    json=initialize_request,
                    timeout=5.0,
                )
                assert response.status_code == 200
                data = response.json()
                # Verify MCP initialize response structure
                assert data["jsonrpc"] == "2.0"
                assert data["id"] == 1
                assert "result" in data
                assert "protocolVersion" in data["result"]
                assert "capabilities" in data["result"]
                assert "serverInfo" in data["result"]
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_tools_list_request(self):
        """Test tools/list request over HTTP."""
        transport = HTTPTransport(host="127.0.0.1", port=8002)
        server = create_server()
        from rmcp.cli import _register_builtin_tools

        _register_builtin_tools(server)
        transport.set_message_handler(server.create_message_handler(transport))
        # Start server in background
        server_task = asyncio.create_task(transport.run())
        await asyncio.sleep(0.1)
        try:
            async with httpx.AsyncClient() as client:
                # First initialize and capture session ID
                initialize_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"},
                    },
                }
                init_response = await client.post(
                    f"http://127.0.0.1:{transport.port}/mcp", json=initialize_request
                )
                session_id = init_response.headers.get("Mcp-Session-Id")
                # Then list tools with session ID
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }
                headers = {}
                if session_id:
                    headers["Mcp-Session-Id"] = session_id
                headers["MCP-Protocol-Version"] = "2025-06-18"
                response = await client.post(
                    f"http://127.0.0.1:{transport.port}/mcp",
                    json=tools_request,
                    headers=headers,
                    timeout=5.0,
                )
                assert response.status_code == 200
                data = response.json()
                # Verify tools list response
                assert data["jsonrpc"] == "2.0"
                assert data["id"] == 2
                assert "result" in data
                assert "tools" in data["result"]
                assert len(data["result"]["tools"]) > 0  # Should have tools
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_tool_call_request(self):
        """Test actual tool call over HTTP."""
        transport = HTTPTransport(host="127.0.0.1", port=8003)
        server = create_server()
        from rmcp.cli import _register_builtin_tools

        _register_builtin_tools(server)
        transport.set_message_handler(server.create_message_handler(transport))
        # Start server in background
        server_task = asyncio.create_task(transport.run())
        await asyncio.sleep(0.1)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Initialize and capture session ID
                initialize_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0.0"},
                    },
                }
                init_response = await client.post(
                    f"http://127.0.0.1:{transport.port}/mcp", json=initialize_request
                )
                session_id = init_response.headers.get("Mcp-Session-Id")
                # Call a simple tool with session ID
                tool_call_request = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "load_example",
                        "arguments": {"dataset_name": "sales"},  # Fixed parameter name
                    },
                }
                headers = {}
                if session_id:
                    headers["Mcp-Session-Id"] = session_id
                headers["MCP-Protocol-Version"] = "2025-06-18"
                response = await client.post(
                    f"http://127.0.0.1:{transport.port}/mcp",
                    json=tool_call_request,
                    headers=headers,
                )
                assert response.status_code == 200
                data = response.json()
                # Verify tool call response
                assert data["jsonrpc"] == "2.0"
                assert data["id"] == 3
                assert "result" in data
                assert "content" in data["result"]
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


class TestHTTPTransportErrorHandling:
    """Test error handling in HTTP transport."""

    @pytest.mark.asyncio
    async def test_invalid_json_request(self):
        """Test handling of invalid JSON requests."""
        transport = HTTPTransport(host="127.0.0.1", port=8004)
        server = create_server()
        transport.set_message_handler(server.create_message_handler(transport))
        # Start server in background
        server_task = asyncio.create_task(transport.run())
        await asyncio.sleep(0.1)
        try:
            async with httpx.AsyncClient() as client:
                # Send invalid JSON
                response = await client.post(
                    f"http://127.0.0.1:{transport.port}/mcp",
                    content="invalid json content",
                    headers={"Content-Type": "application/json"},
                    timeout=5.0,
                )
                assert response.status_code == 400
                assert "Invalid JSON" in response.text
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_malformed_jsonrpc_request(self):
        """Test handling of malformed JSON-RPC requests."""
        transport = HTTPTransport(host="127.0.0.1", port=8005)
        server = create_server()
        transport.set_message_handler(server.create_message_handler(transport))
        # Start server in background
        server_task = asyncio.create_task(transport.run())
        await asyncio.sleep(0.1)
        try:
            async with httpx.AsyncClient() as client:
                # Send malformed JSON-RPC (missing required fields)
                malformed_request = {"not_jsonrpc": "2.0", "invalid": "request"}
                response = await client.post(
                    f"http://127.0.0.1:{transport.port}/mcp",
                    json=malformed_request,
                    timeout=5.0,
                )
                assert response.status_code == 200  # Should return JSON-RPC error
                data = response.json()
                assert "error" in data
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


class TestHTTPTransportSSE:
    """Test Server-Sent Events functionality."""

    @pytest.mark.asyncio
    async def test_sse_connection(self):
        """Test SSE endpoint connection."""
        transport = HTTPTransport(host="127.0.0.1", port=8006)
        server = create_server()
        transport.set_message_handler(server.create_message_handler(transport))
        # Start server in background
        server_task = asyncio.create_task(transport.run())
        await asyncio.sleep(0.1)
        try:
            async with httpx.AsyncClient() as client:
                # Connect to SSE endpoint
                async with client.stream(
                    "GET", f"http://127.0.0.1:{transport.port}/mcp/sse"
                ) as response:
                    assert response.status_code == 200
                    assert response.headers["content-type"].startswith(
                        "text/event-stream"
                    )
                    # Read a few events (should be empty initially)
                    events_received = 0
                    async for _line in response.aiter_lines():
                        events_received += 1
                        if events_received > 2:  # Just check connection works
                            break
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_sse_notification_delivery(self):
        """Test that notifications are delivered via SSE."""
        transport = HTTPTransport(host="127.0.0.1", port=8007)
        server = create_server()
        transport.set_message_handler(server.create_message_handler(transport))
        # Start server in background
        server_task = asyncio.create_task(transport.run())
        await asyncio.sleep(0.1)
        try:
            # Queue a notification
            test_notification = {
                "jsonrpc": "2.0",
                "method": "notification/test",
                "params": {"message": "test notification"},
            }
            await transport.send_message(test_notification)
            # Connect to SSE and check for the notification
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET", f"http://127.0.0.1:{transport.port}/mcp/sse"
                ) as response:
                    assert response.status_code == 200
                    # Read events for a short time
                    timeout_time = time.time() + 2  # 2 second timeout
                    async for line in response.aiter_lines():
                        if time.time() > timeout_time:
                            break
                        if line.startswith("data: "):
                            event_data = line[6:]  # Remove "data: " prefix
                            try:
                                parsed_data = json.loads(event_data)
                                if parsed_data.get("method") == "notification/test":
                                    # Found our notification!
                                    assert (
                                        parsed_data["params"]["message"]
                                        == "test notification"
                                    )
                                    break
                            except json.JSONDecodeError:
                                continue  # Skip malformed data
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


class TestHTTPTransportHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Test the health check endpoint."""
        transport = HTTPTransport(host="127.0.0.1", port=8008)
        server = create_server()
        transport.set_message_handler(server.create_message_handler(transport))
        # Start server in background
        server_task = asyncio.create_task(transport.run())
        await asyncio.sleep(0.1)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:{transport.port}/health", timeout=5.0
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["transport"]["type"] == "HTTP"
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


class TestHTTPTransportCORS:
    """Test CORS functionality."""

    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """Test that CORS headers are properly set."""
        transport = HTTPTransport(host="127.0.0.1", port=8009)
        server = create_server()
        transport.set_message_handler(server.create_message_handler(transport))
        # Start server in background
        server_task = asyncio.create_task(transport.run())
        await asyncio.sleep(0.1)
        try:
            async with httpx.AsyncClient() as client:
                # Send OPTIONS request to check CORS
                response = await client.options(
                    f"http://127.0.0.1:{transport.port}/mcp",
                    headers={"Origin": "http://localhost:3000"},
                    timeout=5.0,
                )
                assert response.status_code == 200
                assert "access-control-allow-origin" in response.headers
                assert "access-control-allow-methods" in response.headers
        finally:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
