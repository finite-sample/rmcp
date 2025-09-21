"""
HTTP transport for MCP server using FastAPI.

Provides HTTP transport following MCP specification:
- POST / for JSON-RPC requests
- GET /sse for Server-Sent Events (notifications)
"""

import asyncio
import json
import logging
import queue
from typing import Any, AsyncIterator

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import Response, StreamingResponse
    import uvicorn
    from sse_starlette import EventSourceResponse
except ImportError as e:
    raise ImportError(
        "HTTP transport requires 'fastapi' extras. Install with: pip install rmcp[http]"
    ) from e

from .base import Transport

logger = logging.getLogger(__name__)


class HTTPTransport(Transport):
    """
    HTTP transport implementation using FastAPI.

    Provides:
    - POST / endpoint for JSON-RPC requests
    - GET /sse endpoint for server-initiated notifications
    - CORS support for web clients
    """

    def __init__(self, host: str = "localhost", port: int = 8000):
        super().__init__("HTTP")
        self.host = host
        self.port = port
        self.app = FastAPI(title="RMCP HTTP Transport", version="1.0.0")
        self._notification_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._setup_routes()
        self._setup_cors()

    def _setup_cors(self) -> None:
        """Configure CORS for web client access."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    def _setup_routes(self) -> None:
        """Setup HTTP routes for MCP communication."""

        @self.app.post("/")
        async def handle_jsonrpc(request: Request) -> dict[str, Any]:
            """Handle JSON-RPC requests via POST."""
            message: dict[str, Any] | None = None
            try:
                message = await request.json()
                logger.debug(f"Received JSON-RPC request: {message}")

                if not self._message_handler:
                    raise HTTPException(500, "Message handler not configured")

                # Process through message handler
                response = await self._message_handler(message)

                logger.debug(f"Sending JSON-RPC response: {response}")
                return response or {}

            except json.JSONDecodeError:
                raise HTTPException(400, "Invalid JSON")
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                base_message = message or {}
                error_response = self._create_error_response(base_message, e)
                if not error_response:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": base_message.get("id"),
                        "error": {"code": -32600, "message": str(e)},
                    }
                return error_response

        async def handle_options(_request: Request) -> Response:
            """Handle CORS preflight requests for the root endpoint."""
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                },
            )

        self.app.router.add_route("/", handle_options, methods=["OPTIONS"])

        @self.app.get("/sse")
        async def handle_sse() -> StreamingResponse:
            """Handle Server-Sent Events for notifications."""

            async def event_generator():
                """Generate SSE events from notification queue."""
                while True:
                    try:
                        notifications_sent = False
                        # Check for notifications (non-blocking)
                        while not self._notification_queue.empty():
                            try:
                                notification = self._notification_queue.get_nowait()
                                yield {
                                    "event": "notification",
                                    "data": json.dumps(notification),
                                }
                                notifications_sent = True
                            except queue.Empty:
                                break

                        if not notifications_sent:
                            yield {
                                "event": "keepalive",
                                "data": json.dumps({"status": "ok"}),
                            }

                        # Small delay to prevent busy waiting
                        await asyncio.sleep(0.5)

                    except asyncio.CancelledError:
                        logger.info("SSE stream cancelled")
                        break
                    except Exception as e:
                        logger.error(f"Error in SSE stream: {e}")
                        break

            return EventSourceResponse(event_generator())

        @self.app.get("/health")
        async def health_check() -> dict[str, str]:
            """Simple health check endpoint."""
            return {"status": "healthy", "transport": "HTTP"}

    async def startup(self) -> None:
        """Initialize the HTTP transport."""
        await super().startup()
        logger.info(f"HTTP transport ready on http://{self.host}:{self.port}")

    async def shutdown(self) -> None:
        """Clean up the HTTP transport."""
        await super().shutdown()
        logger.info("HTTP transport shutdown complete")

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """
        For HTTP transport, messages come via HTTP requests.
        This method is not used as FastAPI handles request routing.
        """
        # HTTP transport doesn't use this pattern - requests come via FastAPI routes
        # This is a no-op to satisfy the abstract method
        if False:  # pragma: no cover
            yield {}

    async def send_message(self, message: dict[str, Any]) -> None:
        """
        Send a message (notification) via SSE.

        For HTTP transport, responses are handled by the HTTP request cycle.
        This is only used for server-initiated notifications.
        """
        if message.get("method"):  # It's a notification
            logger.debug(f"Queuing notification for SSE: {message}")
            self._notification_queue.put(message)
        else:
            # Regular responses are handled by FastAPI return values
            logger.debug("HTTP response handled by FastAPI")

    async def send_progress_notification(
        self, token: str, value: int, total: int, message: str = ""
    ) -> None:
        """Send progress updates over the SSE channel."""

        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/progress",
            "params": {
                "progressToken": token,
                "progress": value,
                "total": total,
                "message": message,
            },
        }
        await self.send_message(notification)

    async def send_log_notification(
        self, level: str, message: str, data: Any = None
    ) -> None:
        """Send structured log messages via SSE."""

        params = {"level": level, "message": message}
        if data:
            params["data"] = data

        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/message",
            "params": params,
        }
        await self.send_message(notification)

    async def run(self) -> None:
        """
        Run the HTTP transport using uvicorn.

        This starts the FastAPI server and handles the HTTP event loop.
        """
        if not self._message_handler:
            raise RuntimeError("Message handler not set")

        try:
            await self.startup()

            # Configure uvicorn
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True,
            )

            server = uvicorn.Server(config)
            logger.info(f"Starting HTTP server on {self.host}:{self.port}")
            await server.serve()

        except Exception as e:
            logger.error(f"HTTP transport error: {e}")
            raise
        finally:
            await self.shutdown()
