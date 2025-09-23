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
import uuid
from typing import Any, AsyncIterator, Dict
from urllib.parse import urlparse

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import Response, StreamingResponse
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
    - MCP protocol compliance with session management and security
    """

    def __init__(self, host: str = "localhost", port: int = 8000):
        super().__init__("HTTP")
        self.host = host
        self.port = port
        # Session management
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._initialized_sessions: set[str] = set()
        # Security validation
        self._is_localhost = host in ("localhost", "127.0.0.1", "::1")
        # Issue security warning for remote binding
        if not self._is_localhost:
            logger.warning(
                f"🚨 SECURITY WARNING: HTTP transport bound to {host}:{port}. "
                "This allows remote access! For production, implement proper authentication. "
                "See https://spec.modelcontextprotocol.io/specification/server/transports/#security"
            )
        self.app = FastAPI(title="RMCP HTTP Transport", version="1.0.0")
        self._notification_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._setup_routes()
        self._setup_cors()

    def _setup_cors(self) -> None:
        """Configure CORS for web client access."""
        # Secure CORS configuration - only allow localhost origins by default
        allowed_origins = (
            ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]
            if self._is_localhost
            else ["*"]
        )  # Allow all for remote (with warning)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    def _validate_origin(self, request: Request) -> None:
        """Validate request origin for security."""
        if self._is_localhost:
            # For localhost binding, ensure origin is also localhost
            origin = request.headers.get("origin")
            if origin:
                parsed = urlparse(origin)
                if parsed.hostname not in ("localhost", "127.0.0.1", None):
                    raise HTTPException(403, "Origin not allowed")

    def _validate_protocol_version(self, request: Request) -> None:
        """Validate MCP-Protocol-Version header."""
        protocol_version = request.headers.get("mcp-protocol-version")
        if not protocol_version:
            # Only require for non-initialize requests in strict mode
            # For now, we'll be lenient but log the issue
            logger.debug("Missing MCP-Protocol-Version header")
        elif protocol_version not in ("2025-06-18",):  # Add supported versions
            logger.warning(f"Unsupported protocol version: {protocol_version}")

    def _get_or_create_session(self, request: Request) -> str:
        """Get or create session ID from headers."""
        session_id = request.headers.get("mcp-session-id")
        if not session_id:
            # Create new session for initialize
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = {
                "created_at": asyncio.get_event_loop().time(),
                "initialized": False,
            }
            logger.debug(f"Created new session: {session_id}")
        return session_id

    def _check_session_initialized(self, session_id: str, method: str) -> None:
        """Check if session is initialized for non-initialize requests."""
        if method != "initialize" and session_id not in self._initialized_sessions:
            raise HTTPException(
                400, "Session not initialized. Send initialize request first."
            )

    def _setup_routes(self) -> None:
        """Setup HTTP routes for MCP communication."""

        @self.app.post("/mcp")
        async def handle_jsonrpc(request: Request) -> Response:
            """Handle JSON-RPC requests via POST."""
            message: dict[str, Any] | None = None
            session_id: str | None = None
            try:
                # Security validations
                self._validate_origin(request)
                self._validate_protocol_version(request)
                # Parse request
                message = await request.json()
                logger.debug(f"Received JSON-RPC request: {message}")
                if not self._message_handler:
                    raise HTTPException(500, "Message handler not configured")
                # Session management
                session_id = self._get_or_create_session(request)
                method = message.get("method", "")
                # Check initialization state
                self._check_session_initialized(session_id, method)
                # Track initialize completion
                if method == "initialize":
                    self._initialized_sessions.add(session_id)
                    self._sessions[session_id]["initialized"] = True
                # Process through message handler
                response = await self._message_handler(message)
                logger.debug(f"Sending JSON-RPC response: {response}")
                # Add session ID to response headers
                headers = {"Mcp-Session-Id": session_id}
                return Response(
                    content=json.dumps(response or {}),
                    media_type="application/json",
                    headers=headers,
                )
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
                # Add session ID to error response if available
                headers = {}
                if session_id:
                    headers["Mcp-Session-Id"] = session_id
                return Response(
                    content=json.dumps(error_response),
                    media_type="application/json",
                    headers=headers,
                )

        async def handle_options(_request: Request) -> Response:
            """Handle CORS preflight requests for MCP endpoints."""
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                },
            )

        # Add CORS support for MCP endpoint
        self.app.router.add_route("/mcp", handle_options, methods=["OPTIONS"])

        # Backward compatibility: redirect root to /mcp
        @self.app.post("/")
        async def redirect_root_post(request: Request) -> Response:
            """Redirect POST / to POST /mcp for backward compatibility."""
            logger.info("Redirecting POST / to POST /mcp for backward compatibility")
            return await handle_jsonrpc(request)

        @self.app.options("/")
        async def redirect_root_options(request: Request) -> Response:
            """Redirect OPTIONS / to OPTIONS /mcp for backward compatibility."""
            return await handle_options(request)

        @self.app.get("/mcp/sse")
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

        # Backward compatibility: redirect /sse to /mcp/sse
        @self.app.get("/sse")
        async def redirect_sse() -> StreamingResponse:
            """Redirect GET /sse to GET /mcp/sse for backward compatibility."""
            logger.info(
                "Redirecting GET /sse to GET /mcp/sse for backward compatibility"
            )
            return await handle_sse()

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
