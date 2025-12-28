"""
HTTP transport for MCP server using FastAPI.
Provides HTTP transport following MCP specification:
- POST /mcp for JSON-RPC requests
- GET /mcp/sse for Server-Sent Events (notifications)
"""

import asyncio
import json
import queue
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

try:
    import uvicorn  # type: ignore
    from fastapi import FastAPI, HTTPException, Request  # type: ignore
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore
    from fastapi.responses import Response  # type: ignore
    from sse_starlette import EventSourceResponse  # type: ignore
except ImportError as e:
    raise ImportError(
        "HTTP transport requires 'fastapi' extras. Install with: pip install rmcp[http]"
    ) from e
from ..config import get_config
from ..core.server import _SUPPORTED_PROTOCOL_VERSIONS
from ..logging_config import (
    LogContext,
    get_logger,
    log_http_request,
    set_correlation_id,
    set_request_id,
)
from .base import Transport

logger = get_logger(__name__)


class HTTPTransport(Transport):
    """
    HTTP transport implementation using FastAPI.
    Provides:
    - POST /mcp endpoint for JSON-RPC requests
    - GET /mcp/sse endpoint for server-initiated notifications
    - MCP protocol compliance with session management and security
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        ssl_keyfile: str | None = None,
        ssl_certfile: str | None = None,
        ssl_keyfile_password: str | None = None,
    ):
        super().__init__("HTTP")

        # Get configuration and use provided values or config defaults
        config = get_config()
        self.host = host or config.http.host
        self.port = port or config.http.port
        self.ssl_keyfile = ssl_keyfile or config.http.ssl_keyfile
        self.ssl_certfile = ssl_certfile or config.http.ssl_certfile
        self.ssl_keyfile_password = (
            ssl_keyfile_password or config.http.ssl_keyfile_password
        )

        # Session management
        self._sessions: dict[str, dict[str, Any]] = {}
        self._initialized_sessions: set[str] = set()

        # SSL/TLS configuration validation
        if self.ssl_keyfile or self.ssl_certfile:
            # First check if both are provided
            if not self.ssl_keyfile:
                raise ValueError(
                    "SSL key file is required when SSL certificate is specified"
                )
            if not self.ssl_certfile:
                raise ValueError(
                    "SSL certificate file is required when SSL key is specified"
                )

            # Only validate file existence if both are specified
            from pathlib import Path

            if not Path(self.ssl_keyfile).is_file():
                raise ValueError(f"SSL key file not found: {self.ssl_keyfile}")
            if not Path(self.ssl_certfile).is_file():
                raise ValueError(f"SSL certificate file not found: {self.ssl_certfile}")

        self.is_https = bool(self.ssl_keyfile and self.ssl_certfile)

        # Security validation
        self._is_localhost = self.host in ("localhost", "127.0.0.1", "::1")
        # Issue security warning for remote binding without HTTPS
        if not self._is_localhost and not self.is_https:
            logger.warning(
                f"🚨 SECURITY WARNING: HTTP transport bound to {self.host}:"
                f"{self.port} without SSL/TLS. "
                "This allows remote access with unencrypted communication! "
                "For production, use HTTPS with --ssl-keyfile and --ssl-certfile. "
                "See https://spec.modelcontextprotocol.io/specification/server/"
                "transports/#security"
            )
        elif not self._is_localhost and self.is_https:
            logger.info(
                f"🔒 HTTPS enabled for remote binding to {self.host}:{self.port}"
            )
        # Import version dynamically to avoid circular imports
        from ..version import get_version

        self.app = FastAPI(
            title="RMCP Statistical Analysis Server",
            version=get_version(),
            description="""
# RMCP: Statistical Analysis through Natural Conversation

A Model Context Protocol (MCP) server providing comprehensive statistical analysis capabilities through R.

## Features

- **53 Statistical Tools** across 11 categories including regression, time series, machine learning, and visualization
- **MCP Protocol Support** - Full compatibility with Claude Desktop and other MCP clients
- **Professional Visualizations** - Generate inline plots and charts
- **Flexible R Integration** - Execute both structured tools and custom R code with security validation
- **Error Recovery** - Intelligent error diagnosis with suggested fixes

## Usage

This server implements the MCP (Model Context Protocol) for statistical analysis.
Use with Claude Desktop or other MCP clients for natural language statistical analysis.

## Getting Started

1. **Initialize Session**: Send an `initialize` request with proper MCP headers
2. **List Tools**: Use `tools/list` to see available statistical analysis tools
3. **Execute Analysis**: Call tools like `linear_model`, `correlation_analysis`, etc.
4. **Get Results**: Receive formatted statistical results with visualizations

## Example Tools

- `linear_model` - Linear and logistic regression analysis
- `correlation_analysis` - Correlation matrices and significance testing
- `time_series_arima` - ARIMA time series modeling and forecasting
- `descriptive_stats` - Comprehensive descriptive statistics
- `scatter_plot` - Professional scatter plots with trend lines

## Documentation

- **Interactive Docs**: Available at `/docs` (Swagger UI)
- **Alternative Docs**: Available at `/redoc` (ReDoc)
- **Health Check**: Available at `/health`
- **GitHub Repository**: [https://github.com/finite-sample/rmcp](https://github.com/finite-sample/rmcp)

## Protocol

This server implements the Model Context Protocol (MCP) specification for statistical analysis tools.
All requests after initialization must include the `MCP-Protocol-Version` header. Use `2025-11-25`
for the latest spec (preferred); `2025-06-18` remains supported for compatibility.
            """.strip(),
            contact={
                "name": "RMCP Project",
                "url": "https://github.com/finite-sample/rmcp",
            },
            license_info={
                "name": "MIT License",
                "url": "https://github.com/finite-sample/rmcp/blob/main/LICENSE",
            },
            openapi_tags=[
                {
                    "name": "MCP Protocol",
                    "description": "Model Context Protocol endpoints for statistical analysis",
                },
                {
                    "name": "Server Management",
                    "description": "Health checks and server information",
                },
                {
                    "name": "Real-time Communications",
                    "description": "Server-Sent Events for notifications and progress updates",
                },
            ],
        )
        self._notification_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._setup_routes()
        self._setup_cors()

    def _setup_cors(self) -> None:
        """Configure CORS for web client access."""
        # Get CORS origins from configuration and add HTTPS versions if SSL is enabled
        config = get_config()
        allowed_origins = list(config.http.cors_origins)

        # If HTTPS is enabled, add HTTPS versions of localhost origins
        if self.is_https:
            https_origins = []
            for origin in config.http.cors_origins:
                if origin.startswith("http://"):
                    https_origin = origin.replace("http://", "https://")
                    https_origins.append(https_origin)
            allowed_origins.extend(https_origins)

        # For remote binding, allow all origins (with security warning already issued)
        if not self._is_localhost:
            allowed_origins = ["*"]
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

    def _validate_protocol_version(self, request: Request, method: str) -> None:
        """Validate MCP-Protocol-Version header according to MCP specification."""
        protocol_version = request.headers.get("mcp-protocol-version")
        supported_versions = _SUPPORTED_PROTOCOL_VERSIONS
        preferred_version = supported_versions[0]

        if method == "initialize":
            # Initialize requests don't require the header (it's set after negotiation)
            if not protocol_version:
                # Default to the latest version when the client doesn't specify one
                request.state.protocol_version = preferred_version
                return
            if protocol_version not in supported_versions:
                raise HTTPException(
                    400,
                    f"Unsupported protocol version: {protocol_version}. "
                    f"Supported versions: {', '.join(supported_versions)}",
                )
            if protocol_version != preferred_version:
                logger.info(
                    "Client requested older MCP protocol version %s; "
                    "preferring %s for responses",
                    protocol_version,
                    preferred_version,
                )
            request.state.protocol_version = protocol_version
        else:
            # All non-initialize requests MUST include the MCP-Protocol-Version header
            if not protocol_version:
                raise HTTPException(
                    400,
                    "Missing required MCP-Protocol-Version header. "
                    "All requests after initialization must include this header.",
                )
            if protocol_version not in supported_versions:
                raise HTTPException(
                    400,
                    f"Unsupported protocol version: {protocol_version}. "
                    f"Supported versions: {', '.join(supported_versions)}",
                )

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

        @self.app.post(
            "/mcp",
            tags=["MCP Protocol"],
            summary="MCP JSON-RPC Endpoint",
            description="""
            Main endpoint for Model Context Protocol communication.

            Handles JSON-RPC 2.0 requests for:
            - Session initialization
            - Tool listing and execution
            - Resource access
            - Statistical analysis operations

            **Required Headers:**
            - `Content-Type: application/json`
            - `MCP-Protocol-Version: 2025-11-25` (preferred after initialization; `2025-06-18`
              remains supported)

            **Session Management:**
            Sessions must be initialized before other operations.
            """,
            response_description="JSON-RPC 2.0 response with results or errors",
        )
        async def handle_jsonrpc(request: Request) -> Response:
            """Handle JSON-RPC requests via POST."""
            message: dict[str, Any]
            session_id: str | None = None
            start_time = time.time()

            # Set up request correlation for observability
            correlation_id = set_correlation_id()
            request_id = set_request_id()

            try:
                # Parse request first to get method for protocol validation
                json_data = await request.json()
                message = json_data if json_data is not None else {}
                method = message.get("method", "")

                with LogContext(correlation_id=correlation_id, request_id=request_id):
                    logger.info(
                        "Processing JSON-RPC request",
                        method=method,
                        message_id=message.get("id"),
                    )

                # Security validations
                self._validate_origin(request)
                self._validate_protocol_version(request, method)

                if not self._message_handler:
                    raise HTTPException(500, "Message handler not configured")
                # Session management
                session_id = self._get_or_create_session(request)

                # Set session context for structured logging
                from ..logging_config import set_session_id

                set_session_id(session_id)

                # Check initialization state
                self._check_session_initialized(session_id, method)
                # Track initialize completion
                if method == "initialize":
                    params = message.setdefault("params", {})
                    if "protocolVersion" not in params and hasattr(
                        request.state, "protocol_version"
                    ):
                        params["protocolVersion"] = request.state.protocol_version
                    self._initialized_sessions.add(session_id)
                    self._sessions[session_id]["initialized"] = True

                    # Log session initialization
                    logger.info(
                        "MCP session initialized",
                        session_id=session_id,
                        protocol_version=params.get("protocolVersion"),
                        client_info=params.get("clientInfo"),
                    )
                # Process through message handler
                response = await self._message_handler(message)

                # Log successful request with timing
                response_time_ms = int((time.time() - start_time) * 1000)
                with LogContext(correlation_id=correlation_id, request_id=request_id):
                    log_http_request(
                        logger,
                        "POST",
                        "/mcp",
                        200,
                        response_time_ms,
                        user_agent=request.headers.get("user-agent"),
                        content_length=len(json.dumps(response or {})),
                    )

                # Add session ID to response headers
                headers = {"Mcp-Session-Id": session_id}
                return Response(
                    content=json.dumps(response or {}),
                    media_type="application/json",
                    headers=headers,
                )
            except json.JSONDecodeError:
                # Log JSON decode error with request correlation
                response_time_ms = int((time.time() - start_time) * 1000)
                with LogContext(correlation_id=correlation_id, request_id=request_id):
                    log_http_request(logger, "POST", "/mcp", 400, response_time_ms)
                raise HTTPException(400, "Invalid JSON")
            except Exception as e:
                # Log error with full context
                response_time_ms = int((time.time() - start_time) * 1000)
                with LogContext(correlation_id=correlation_id, request_id=request_id):
                    log_http_request(logger, "POST", "/mcp", 500, response_time_ms)
                    logger.error(
                        "Request processing failed",
                        error=str(e),
                        method=message.get("method") if message else "unknown",
                    )

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

        @self.app.get(
            "/mcp/sse",
            tags=["Real-time Communications"],
            summary="Server-Sent Events Endpoint",
            description="""
            Server-Sent Events (SSE) endpoint for real-time notifications.

            Provides:
            - Progress updates during long-running statistical operations
            - Log messages and warnings
            - Keep-alive signals

            **Connection:**
            Standard EventSource connection. Events are JSON-encoded.

            **Event Types:**
            - `notification`: Statistical analysis progress/results
            - `keepalive`: Connection health check
            """,
            response_description="Server-Sent Events stream",
        )
        async def handle_sse() -> EventSourceResponse:
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

        @self.app.get(
            "/",
            tags=["Server Management"],
            summary="Server Landing Page",
            description="Landing page with server information and navigation links",
            response_description="HTML landing page",
        )
        async def landing_page() -> Response:
            """Server landing page with information and navigation."""
            html_content = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>RMCP Statistical Analysis Server</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                           margin: 0; padding: 40px; background: #f8f9fa; color: #333; }
                    .container { max-width: 800px; margin: 0 auto; background: white;
                                padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    h1 { color: #2c3e50; margin-bottom: 10px; }
                    .subtitle { color: #7f8c8d; font-size: 18px; margin-bottom: 30px; }
                    .status { display: inline-block; background: #27ae60; color: white;
                             padding: 4px 12px; border-radius: 20px; font-size: 14px; margin-bottom: 30px; }
                    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                           gap: 20px; margin: 30px 0; }
                    .card { border: 1px solid #ddd; border-radius: 6px; padding: 20px; }
                    .card h3 { margin-top: 0; color: #2c3e50; }
                    .btn { display: inline-block; background: #3498db; color: white;
                          text-decoration: none; padding: 10px 20px; border-radius: 4px; margin: 5px 0; }
                    .btn:hover { background: #2980b9; }
                    .btn-secondary { background: #95a5a6; }
                    .btn-secondary:hover { background: #7f8c8d; }
                    .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee;
                             text-align: center; color: #7f8c8d; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🔬 RMCP Statistical Analysis Server</h1>
                    <p class="subtitle">Statistical Analysis through Natural Conversation</p>
                    <div class="status">✅ Server Online</div>

                    <p>This server provides comprehensive statistical analysis capabilities through the Model Context Protocol (MCP).
                    Access 53 statistical tools including regression, time series analysis, machine learning, and professional visualizations.</p>

                    <div class="grid">
                        <div class="card">
                            <h3>📚 Interactive Documentation</h3>
                            <p>Explore the API with Swagger UI and ReDoc interfaces</p>
                            <a href="/docs" class="btn">Swagger UI</a>
                            <a href="/redoc" class="btn btn-secondary">ReDoc</a>
                        </div>

                        <div class="card">
                            <h3>🔧 Server Status</h3>
                            <p>Monitor server health and check system status</p>
                            <a href="/health" class="btn">Health Check</a>
                            <a href="/mcp/sse" class="btn btn-secondary">Event Stream</a>
                        </div>

                        <div class="card">
                            <h3>💡 Getting Started</h3>
                            <p>Learn how to use RMCP for statistical analysis</p>
                            <a href="https://github.com/finite-sample/rmcp" class="btn">GitHub Repository</a>
                            <a href="https://finite-sample.github.io/rmcp/" class="btn btn-secondary">Documentation</a>
                        </div>
                    </div>

                    <h3>🚀 Quick Start</h3>
                    <p><strong>For Claude Desktop Users:</strong></p>
                    <pre style="background: #f4f4f4; padding: 15px; border-radius: 4px; overflow-x: auto;">
{
  "mcpServers": {
    "rmcp": {
      "command": "rmcp",
      "args": ["start"]
    }
  }
}</pre>

                    <p><strong>For HTTP API Users:</strong></p>
                    <pre style="background: #f4f4f4; padding: 15px; border-radius: 4px; overflow-x: auto;">
curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \\
  -H "Content-Type: application/json" \\
  -H "MCP-Protocol-Version: 2025-11-25" \\
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0"}}}'</pre>

                    <div class="footer">
                        <p>RMCP v0.5.1 | MIT License | <a href="https://github.com/finite-sample/rmcp">GitHub</a></p>
                    </div>
                </div>
            </body>
            </html>
            """
            return Response(content=html_content, media_type="text/html")

        @self.app.get(
            "/health",
            tags=["Server Management"],
            summary="Health Check",
            description="""
            Comprehensive health check endpoint for monitoring server status.

            Returns detailed server health information including:
            - Server status and uptime
            - R environment availability
            - Transport configuration
            - Active connections count
            - System health indicators

            Useful for load balancers, monitoring systems, and deployment validation.
            """,
            response_description="Detailed server health status",
        )
        async def health_check() -> dict[str, Any]:
            """Comprehensive health check endpoint."""
            import time

            from ..r_integration import get_r_binary_path

            health_data = {
                "status": "healthy",
                "timestamp": time.time(),
                "transport": {"type": "HTTP", "host": self.host, "port": self.port},
                "connections": {
                    "active_sessions": len(self._initialized_sessions),
                    "notification_queue_size": self._notification_queue.qsize(),
                },
            }

            # Check R availability
            try:
                r_path = get_r_binary_path()
                health_data["r_environment"] = {
                    "available": True,
                    "binary_path": r_path,
                    "status": "ready",
                }
            except Exception as e:
                health_data["r_environment"] = {
                    "available": False,
                    "error": str(e),
                    "status": "unavailable",
                }
                health_data["status"] = "degraded"

            return health_data

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
            # Configure uvicorn with SSL support
            config_params = {
                "app": self.app,
                "host": self.host,
                "port": self.port,
                "log_level": "info",
                "access_log": True,
            }

            # Add SSL configuration if enabled
            if self.is_https:
                config_params.update(
                    {
                        "ssl_keyfile": self.ssl_keyfile,
                        "ssl_certfile": self.ssl_certfile,
                    }
                )
                if self.ssl_keyfile_password:
                    config_params["ssl_keyfile_password"] = self.ssl_keyfile_password

            config = uvicorn.Config(**config_params)
            server = uvicorn.Server(config)
            protocol = "HTTPS" if self.is_https else "HTTP"
            logger.info(f"Starting {protocol} server on {self.host}:{self.port}")
            await server.serve()
        except Exception as e:
            logger.error(f"HTTP transport error: {e}")
            raise
        finally:
            await self.shutdown()
