"""
SDK-based transports: stdio and spec-compliant Streamable HTTP.

Both transports drive the official MCP SDK server built by
:mod:`rmcp.core.sdk_adapter`, replacing the previous hand-rolled
JSON-RPC transports.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from ..core.sdk_adapter import build_sdk_server

if TYPE_CHECKING:
    from ..core.server import MCPServer

logger = logging.getLogger(__name__)


async def run_stdio(rmcp_server: MCPServer) -> None:
    """Run the server over stdio using the official SDK transport."""
    adapter = build_sdk_server(rmcp_server)
    await rmcp_server.startup()
    try:
        async with stdio_server() as (read_stream, write_stream):
            await adapter.sdk_server.run(
                read_stream,
                write_stream,
                adapter.initialization_options(),
            )
    finally:
        await rmcp_server.shutdown()


class _MCPPathNormalizerMiddleware:
    """Rewrite the exact ``/mcp`` path to ``/mcp/``.

    Starlette's ``Mount`` otherwise answers ``POST /mcp`` with a 307 redirect,
    which strict MCP clients (that don't follow redirects) treat as an error.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "http" and scope.get("path") == "/mcp":
            scope = dict(scope)
            scope["path"] = "/mcp/"
            if "raw_path" in scope:
                scope["raw_path"] = b"/mcp/"
        await self.app(scope, receive, send)


class BearerAuthMiddleware:
    """Minimal bearer-token auth for the /mcp endpoint.

    ``/health`` (and any non-/mcp path) stays open. Configure keys via
    ``api_keys``; with an empty key set the middleware is a pass-through.
    """

    def __init__(self, app: ASGIApp, api_keys: set[str]):
        self.app = app
        self.api_keys = {key for key in api_keys if key}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.api_keys or scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        authorization = headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip() in self.api_keys:
            await self.app(scope, receive, send)
            return
        response = JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32001, "message": "Unauthorized"},
            },
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)


def create_streamable_http_app(
    rmcp_server: MCPServer,
    *,
    api_keys: set[str] | None = None,
    cors_origins: list[str] | None = None,
    json_response: bool = False,
    stateless: bool = False,
    manage_server_lifecycle: bool = True,
) -> Starlette:
    """Build a Starlette app serving MCP Streamable HTTP at ``/mcp``.

    Args:
        rmcp_server: Configured RMCP server with registered tools.
        api_keys: Bearer tokens accepted on /mcp. Empty/None disables auth.
        cors_origins: Allowed CORS origins (defaults to ``["*"]``).
        json_response: Return plain JSON instead of SSE streams.
        stateless: Run sessions statelessly (fresh transport per request).
        manage_server_lifecycle: Run rmcp startup/shutdown with the app lifespan.
    """
    adapter = build_sdk_server(rmcp_server)
    session_manager = StreamableHTTPSessionManager(
        app=adapter.sdk_server,
        event_store=None,
        json_response=json_response,
        stateless=stateless,
    )

    async def handle_mcp(scope: Scope, receive: Receive, send: Send) -> None:
        await session_manager.handle_request(scope, receive, send)

    async def health(request: Request) -> Response:
        return JSONResponse(
            {
                "status": "healthy",
                "server": rmcp_server.name,
                "version": rmcp_server.version,
                "transport": "streamable-http",
                "tools": len(rmcp_server.tools._tools),
            }
        )

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            if manage_server_lifecycle:
                await rmcp_server.startup()
            try:
                yield
            finally:
                if manage_server_lifecycle:
                    await rmcp_server.shutdown()

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=cors_origins or ["*"],
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["Mcp-Session-Id"],
        ),
        Middleware(BearerAuthMiddleware, api_keys=api_keys or set()),
        Middleware(_MCPPathNormalizerMiddleware),
    ]

    return Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Mount("/mcp", app=handle_mcp),
        ],
        middleware=middleware,
        lifespan=lifespan,
    )


def run_streamable_http(
    rmcp_server: MCPServer,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    api_keys: set[str] | None = None,
    cors_origins: list[str] | None = None,
    ssl_keyfile: str | None = None,
    ssl_certfile: str | None = None,
    ssl_keyfile_password: str | None = None,
    log_level: str = "info",
) -> None:
    """Serve the Streamable HTTP app with uvicorn (blocking)."""
    import uvicorn

    if bool(ssl_keyfile) != bool(ssl_certfile):
        raise ValueError(
            "Both --ssl-keyfile and --ssl-certfile are required to enable HTTPS"
        )
    for label, ssl_path in (("keyfile", ssl_keyfile), ("certfile", ssl_certfile)):
        if ssl_path and not Path(ssl_path).exists():
            raise FileNotFoundError(f"SSL {label} not found: {ssl_path}")

    app = create_streamable_http_app(
        rmcp_server,
        api_keys=api_keys,
        cors_origins=cors_origins,
    )
    uvicorn_kwargs: dict[str, Any] = {
        "host": host,
        "port": port,
        "log_level": log_level.lower(),
    }
    if ssl_keyfile and ssl_certfile:
        uvicorn_kwargs.update(
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            ssl_keyfile_password=ssl_keyfile_password,
        )
    uvicorn.run(app, **uvicorn_kwargs)
