"""
Unit tests for HTTP transport implementation.
Tests the HTTPTransport class functionality including:
- Initialization and configuration
- FastAPI app setup
- Route registration
- Message handling
- SSE notification queueing
- Error handling
"""

import asyncio
import queue
from unittest.mock import AsyncMock, patch

import pytest

# Skip tests if FastAPI not available
fastapi = pytest.importorskip("fastapi", reason="FastAPI not available")
uvicorn = pytest.importorskip("uvicorn", reason="uvicorn not available")
from rmcp.core.server import create_server  # noqa: E402
from rmcp.transport.http import HTTPTransport  # noqa: E402


class TestHTTPTransportInitialization:
    """Test HTTP transport initialization and configuration."""

    def test_default_initialization(self):
        """Test HTTPTransport with default parameters."""
        transport = HTTPTransport()
        assert transport.name == "HTTP"
        assert transport.host == "localhost"
        assert transport.port == 8000
        assert transport.app is not None
        assert transport.app.title == "RMCP Statistical Analysis Server"
        assert not transport.is_running

    def test_custom_initialization(self):
        """Test HTTPTransport with custom host and port."""
        transport = HTTPTransport(host="0.0.0.0", port=9000)
        assert transport.host == "0.0.0.0"
        assert transport.port == 9000
        assert transport.name == "HTTP"

    def test_fastapi_app_configuration(self):
        """Test that FastAPI app is properly configured."""
        transport = HTTPTransport()
        # Check that the app has expected routes
        route_paths = [route.path for route in transport.app.routes]
        assert "/" in route_paths
        assert "/mcp/sse" in route_paths
        assert "/health" in route_paths

    def test_message_handler_setting(self):
        """Test setting the message handler."""
        transport = HTTPTransport()
        mock_handler = AsyncMock()
        transport.set_message_handler(mock_handler)
        assert transport._message_handler == mock_handler

    def test_notification_queue_initialization(self):
        """Test that notification queue is properly initialized."""
        transport = HTTPTransport()
        assert isinstance(transport._notification_queue, queue.Queue)
        assert transport._notification_queue.empty()


class TestHTTPTransportLifecycle:
    """Test HTTP transport lifecycle management."""

    @pytest.mark.asyncio
    async def test_startup(self):
        """Test transport startup."""
        transport = HTTPTransport()
        await transport.startup()
        assert transport.is_running

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test transport shutdown."""
        transport = HTTPTransport()
        await transport.startup()
        await transport.shutdown()
        assert not transport.is_running

    @pytest.mark.asyncio
    async def test_lifecycle_logging(self):
        """Test that lifecycle events are logged."""
        transport = HTTPTransport()
        with patch("rmcp.transport.http.logger") as mock_logger:
            await transport.startup()
            mock_logger.info.assert_called_with(
                "HTTP transport ready on http://localhost:8000"
            )
            await transport.shutdown()
            mock_logger.info.assert_called_with("HTTP transport shutdown complete")


class TestHTTPTransportMessageHandling:
    """Test HTTP transport message handling."""

    def test_send_notification(self):
        """Test sending notifications via SSE queue."""
        transport = HTTPTransport()
        notification = {
            "jsonrpc": "2.0",
            "method": "notification/test",
            "params": {"data": "test"},
        }
        asyncio.run(transport.send_message(notification))
        # Check that notification was queued
        assert not transport._notification_queue.empty()
        queued_notification = transport._notification_queue.get()
        assert queued_notification == notification

    def test_send_non_notification(self):
        """Test sending non-notification messages (should not queue)."""
        transport = HTTPTransport()
        response = {"jsonrpc": "2.0", "id": 1, "result": {"data": "test"}}
        asyncio.run(transport.send_message(response))
        # Should not be queued (responses handled by FastAPI)
        assert transport._notification_queue.empty()

    @pytest.mark.asyncio
    async def test_receive_messages_not_used(self):
        """Test that receive_messages is not used in HTTP transport."""
        transport = HTTPTransport()
        # This should be a no-op iterator
        async for _message in transport.receive_messages():
            # Should never execute
            raise AssertionError("receive_messages should not yield anything")


class TestHTTPTransportErrorHandling:
    """Test HTTP transport error handling."""

    def test_create_error_response_with_id(self):
        """Test error response creation for requests with ID."""
        transport = HTTPTransport()
        request = {"jsonrpc": "2.0", "id": 1, "method": "test"}
        error = ValueError("Test error")
        error_response = transport._create_error_response(request, error)
        assert error_response is not None
        assert error_response["jsonrpc"] == "2.0"
        assert error_response["id"] == 1
        assert error_response["error"]["code"] == -32603
        assert error_response["error"]["message"] == "Test error"
        assert error_response["error"]["data"]["type"] == "ValueError"

    def test_create_error_response_without_id(self):
        """Test error response creation for notifications (no ID)."""
        transport = HTTPTransport()
        notification = {"jsonrpc": "2.0", "method": "test"}
        error = ValueError("Test error")
        error_response = transport._create_error_response(notification, error)
        assert error_response is None  # No response for notifications


class TestHTTPTransportIntegrationWithServer:
    """Test HTTP transport integration with MCP server."""

    @pytest.mark.asyncio
    async def test_integration_with_server(self):
        """Test that HTTP transport can be integrated with MCP server."""
        # Create server and transport
        server = create_server()
        transport = HTTPTransport()
        # Set up integration
        transport.set_message_handler(server.create_message_handler(transport))
        # Verify setup
        assert callable(transport._message_handler)

    def test_run_method_requires_handler(self):
        """Test that run method requires message handler to be set."""
        transport = HTTPTransport()
        with pytest.raises(RuntimeError, match="Message handler not set"):
            asyncio.run(transport.run())


@pytest.mark.skipif(not fastapi, reason="FastAPI not available")
class TestHTTPTransportFastAPIIntegration:
    """Test FastAPI-specific functionality."""

    def test_fastapi_routes_registration(self):
        """Test that all expected routes are registered with FastAPI."""
        transport = HTTPTransport()
        app = transport.app
        # Get route methods and paths
        routes_info = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    routes_info.append((method, route.path))
        # Check expected endpoints
        assert ("POST", "/mcp") in routes_info
        assert ("GET", "/mcp/sse") in routes_info
        assert ("GET", "/health") in routes_info

    def test_cors_middleware(self):
        """Test that CORS middleware is configured."""
        transport = HTTPTransport()
        app = transport.app
        # Check that CORS middleware is added
        middleware_types = [mw.cls.__name__ for mw in app.user_middleware]
        assert "CORSMiddleware" in middleware_types

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test the health check endpoint."""
        from fastapi.testclient import TestClient

        transport = HTTPTransport()
        client = TestClient(transport.app)
        response = client.get("/health")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "healthy"
        assert response_data["transport"]["type"] == "HTTP"


class TestHTTPTransportImportError:
    """Test behavior when FastAPI dependencies are missing."""

    def test_import_error_handling(self):
        """Test that ImportError is properly handled and re-raised."""
        import importlib
        import sys

        sys.modules.pop("rmcp.transport.http", None)
        with patch.dict(
            sys.modules,
            {
                "fastapi": None,
                "uvicorn": None,
                "sse_starlette": None,
            },
            clear=False,
        ):
            with pytest.raises(
                ImportError, match="HTTP transport requires 'fastapi' extras"
            ):
                importlib.import_module("rmcp.transport.http")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
