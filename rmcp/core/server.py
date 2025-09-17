"""
MCP Server shell with lifecycle hooks.

This module provides the main server class that:
- Initializes the MCP app using official SDK
- Manages lifespan hooks (startup/shutdown)
- Composes transports at the edge
- Centralizes registry management

Following the principle: "A single shell centralizes initialization and teardown."
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..registries.prompts import PromptsRegistry
from ..registries.resources import ResourcesRegistry
from ..registries.tools import ToolsRegistry
from ..security.vfs import VFS
from .context import Context, LifespanState, RequestState

# Official MCP SDK imports (to be added when SDK is available)
# from mcp import Server, initialize_server
# from mcp.types import Request, Response, Notification


logger = logging.getLogger(__name__)


class MCPServer:
    """
    Main MCP server shell that manages lifecycle and registries.

    This class serves as the central orchestrator for the RMCP MCP server, providing:
    - Lifespan management (startup/shutdown hooks)
    - Registry composition (tools/resources/prompts)
    - Security policy enforcement via VFS
    - Transport-agnostic request handling
    - Request tracking and cancellation support

    The server follows the Model Context Protocol (MCP) specification for
    communication with AI assistants like Claude Desktop.

    Example:
        >>> server = MCPServer(name="My Server", version="1.0.0")
        >>> server.configure(allowed_paths=["/data"], read_only=True)
        >>> # Register tools, prompts, resources...
        >>> await server.startup()
    """

    def __init__(
        self,
        name: str = "RMCP MCP Server",
        version: str = "0.3.3",
        description: str = "R-based statistical analysis MCP server",
    ):
        """
        Initialize the MCP server instance.

        Args:
            name: Human-readable name for the server
            version: Semantic version string
            description: Brief description of server capabilities
        """
        self.name = name
        self.version = version
        self.description = description

        # Lifespan state
        self.lifespan_state = LifespanState()

        # Registries
        self.tools = ToolsRegistry()
        self.resources = ResourcesRegistry()
        self.prompts = PromptsRegistry()

        # Security
        self.vfs: Optional[VFS] = None

        # Callbacks
        self._startup_callbacks: List[Callable[[], Awaitable[None]]] = []
        self._shutdown_callbacks: List[Callable[[], Awaitable[None]]] = []

        # Request tracking for cancellation
        self._active_requests: Dict[str, RequestState] = {}

    def configure(
        self,
        allowed_paths: Optional[List[str]] = None,
        cache_root: Optional[str] = None,
        read_only: bool = True,
        **settings: Any,
    ) -> "MCPServer":
        """
        Configure server security and operational settings.

        Args:
            allowed_paths: List of filesystem paths the server can access.
                If None, defaults to current working directory.
            cache_root: Directory for caching intermediate results.
                Created if it doesn't exist.
            read_only: Whether filesystem access is read-only.
                Recommended for production deployments.
            **settings: Additional configuration options passed to lifespan state.

        Returns:
            Self for method chaining.

        Example:
            >>> server.configure(
            ...     allowed_paths=["/data", "/models"],
            ...     cache_root="/tmp/rmcp_cache",
            ...     read_only=True
            ... )
        """

        if allowed_paths:
            self.lifespan_state.allowed_paths = [Path(p) for p in allowed_paths]

        if cache_root:
            cache_path = Path(cache_root)
            cache_path.mkdir(parents=True, exist_ok=True)
            self.lifespan_state.cache_root = cache_path

        self.lifespan_state.read_only = read_only
        self.lifespan_state.settings.update(settings)

        # Initialize VFS
        self.vfs = VFS(
            allowed_roots=self.lifespan_state.allowed_paths, read_only=read_only
        )

        return self

    def on_startup(
        self, func: Callable[[], Awaitable[None]]
    ) -> Callable[[], Awaitable[None]]:
        """
        Register a callback to run during server startup.

        Args:
            func: Async function to call during startup. Should not take arguments.

        Returns:
            The same function (for use as decorator).

        Example:
            >>> @server.on_startup
            ... async def initialize_r_packages():
            ...     # Check R installation, load packages, etc.
            ...     pass
        """
        self._startup_callbacks.append(func)
        return func

    def on_shutdown(
        self, func: Callable[[], Awaitable[None]]
    ) -> Callable[[], Awaitable[None]]:
        """
        Register a callback to run during server shutdown.

        Args:
            func: Async function to call during shutdown. Should not take arguments.

        Returns:
            The same function (for use as decorator).

        Example:
            >>> @server.on_shutdown
            ... async def cleanup_temp_files():
            ...     # Clean up R temporary files, connections, etc.
            ...     pass
        """
        self._shutdown_callbacks.append(func)
        return func

    async def startup(self) -> None:
        """
        Start the server and run all startup callbacks.

        This method should be called once before handling any requests.
        It executes all registered startup callbacks in registration order.

        Raises:
            Exception: If any startup callback fails, the exception propagates.
        """
        logger.info(f"Starting {self.name} v{self.version}")

        for callback in self._startup_callbacks:
            await callback()

        logger.info("Server startup complete")

    async def shutdown(self) -> None:
        """
        Shutdown the server gracefully.

        This method:
        1. Cancels all active requests
        2. Runs all shutdown callbacks (continuing on errors)
        3. Logs completion

        Shutdown callbacks are called in registration order and errors
        are logged but don't prevent other callbacks from running.
        """
        logger.info("Shutting down server")

        # Cancel active requests
        for request in self._active_requests.values():
            request.cancel()

        # Run shutdown callbacks
        for callback in self._shutdown_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}")

        logger.info("Server shutdown complete")

    def create_context(
        self,
        request_id: str,
        method: str,
        progress_token: Optional[str] = None,
    ) -> Context:
        """
        Create execution context for a request.

        Args:
            request_id: Unique identifier for the request
            method: MCP method being called (e.g., "tools/call")
            progress_token: Optional token for progress reporting

        Returns:
            Context object with progress/logging callbacks configured
        """

        async def progress_callback(message: str, current: int, total: int) -> None:
            # TODO: Send MCP progress notification
            logger.info(f"Progress {request_id}: {message} ({current}/{total})")

        async def log_callback(level: str, message: str, data: Dict[str, Any]) -> None:
            # TODO: Send MCP log notification
            log_level = getattr(logging, level.upper(), logging.INFO)
            logger.log(log_level, f"{request_id}: {message} {data}")

        context = Context.create(
            request_id=request_id,
            method=method,
            lifespan_state=self.lifespan_state,
            progress_token=progress_token,
            progress_callback=progress_callback,
            log_callback=log_callback,
        )

        # Track request for cancellation
        self._active_requests[request_id] = context.request

        return context

    def finish_request(self, request_id: str) -> None:
        """
        Clean up request tracking after completion.

        Args:
            request_id: The request ID to remove from active tracking
        """
        self._active_requests.pop(request_id, None)

    async def cancel_request(self, request_id: str) -> None:
        """
        Cancel an active request by ID.

        Args:
            request_id: The request ID to cancel

        Note:
            If the request is not found, this method does nothing.
            Cancellation is cooperative - the request handler must
            check for cancellation periodically.
        """
        if request_id in self._active_requests:
            self._active_requests[request_id].cancel()
            logger.info(f"Cancelled request {request_id}")

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP initialize request.

        Returns server capabilities and metadata according to MCP protocol.

        Args:
            params: Initialize parameters from client

        Returns:
            Initialize response with server capabilities
        """
        client_info = params.get("clientInfo", {})
        logger.info(
            f"Initializing MCP connection with client: {client_info.get('name', 'unknown')}"
        )

        return {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
                "logging": {"level": "info"},
            },
            "serverInfo": {"name": self.name, "version": self.version},
        }

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle incoming MCP request and route to appropriate handler.

        This is the main entry point for all MCP requests. It:
        1. Extracts method, ID, and parameters from the request
        2. Routes to appropriate registry (tools, resources, prompts)
        3. Returns properly formatted JSON-RPC response
        4. Handles errors with appropriate error codes

        Args:
            request: JSON-RPC request dict with method, id, and params

        Returns:
            JSON-RPC response dict or None for notifications

        Supported methods:
            - initialize: Initialize MCP connection and return capabilities
            - tools/list: List available tools
            - tools/call: Execute a tool with parameters
            - resources/list: List available resources
            - resources/read: Read a resource by URI
            - prompts/list: List available prompts
            - prompts/get: Get a prompt with arguments
        """
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})

        # Handle notifications (no response expected)
        if request_id is None:
            await self._handle_notification(method, params)
            return None

        try:
            context = self.create_context(request_id, method)

            # Route to appropriate handler
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self.tools.list_tools(context)
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.tools.call_tool(context, tool_name, arguments)
            elif method == "resources/list":
                result = await self.resources.list_resources(context)
            elif method == "resources/read":
                uri = params.get("uri")
                result = await self.resources.read_resource(context, uri)
            elif method == "prompts/list":
                result = await self.prompts.list_prompts(context)
            elif method == "prompts/get":
                name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.prompts.get_prompt(context, name, arguments)
            else:
                raise ValueError(f"Unknown method: {method}")

            return {"jsonrpc": "2.0", "id": request_id, "result": result}

        except Exception as e:
            logger.error(f"Error handling request {request_id}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)},  # Internal error
            }

        finally:
            if request_id:
                self.finish_request(request_id)

    async def _handle_notification(self, method: str, params: Dict[str, Any]) -> None:
        """
        Handle MCP notification messages (no response expected).

        Args:
            method: Notification method name
            params: Notification parameters

        Supported notifications:
            - notifications/cancelled: Request cancellation
            - notifications/initialized: Client initialization complete
        """
        logger.info(f"Received notification: {method}")

        if method == "notifications/cancelled":
            # Handle cancellation notification
            request_id = params.get("requestId")
            if request_id:
                await self.cancel_request(request_id)

        elif method == "notifications/initialized":
            # MCP initialization complete
            logger.info("MCP client initialization complete")

        else:
            logger.warning(f"Unknown notification method: {method}")


def create_server(
    name: str = "RMCP MCP Server",
    version: str = "0.3.3",
    description: str = "R-based statistical analysis MCP server",
) -> MCPServer:
    """
    Factory function to create a new MCP server instance.

    Args:
        name: Human-readable server name
        version: Semantic version string
        description: Brief description of server capabilities

    Returns:
        Configured MCPServer instance ready for configuration and startup

    Example:
        >>> server = create_server(
        ...     name="My Analytics Server",
        ...     version="1.0.0",
        ...     description="Custom R analytics tools"
        ... )
        >>> server.configure(allowed_paths=["/data"])
    """
    return MCPServer(name=name, version=version, description=description)
