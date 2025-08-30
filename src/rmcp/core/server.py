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
from typing import Any, Dict, Optional, Callable, Awaitable, List
from pathlib import Path
import sys

# Official MCP SDK imports (to be added when SDK is available)
# from mcp import Server, initialize_server
# from mcp.types import Request, Response, Notification

from .context import Context, LifespanState, RequestState
from ..registries.tools import ToolsRegistry  
from ..registries.resources import ResourcesRegistry
from ..registries.prompts import PromptsRegistry
from ..security.vfs import VFS

logger = logging.getLogger(__name__)


class MCPServer:
    """
    Main MCP server shell that manages lifecycle and registries.
    
    Centralizes:
    - Lifespan management (startup/shutdown)
    - Registry composition (tools/resources/prompts)
    - Security policy enforcement
    - Transport-agnostic request handling
    """
    
    def __init__(
        self,
        name: str = "RMCP MCP Server",
        version: str = "0.3.2",
        description: str = "R-based statistical analysis MCP server",
    ):
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
        """Configure server settings."""
        
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
            allowed_roots=self.lifespan_state.allowed_paths,
            read_only=read_only
        )
        
        return self
    
    def on_startup(self, func: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
        """Register startup callback."""
        self._startup_callbacks.append(func)
        return func
    
    def on_shutdown(self, func: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
        """Register shutdown callback.""" 
        self._shutdown_callbacks.append(func)
        return func
    
    async def startup(self) -> None:
        """Run startup callbacks."""
        logger.info(f"Starting {self.name} v{self.version}")
        
        for callback in self._startup_callbacks:
            await callback()
        
        logger.info("Server startup complete")
    
    async def shutdown(self) -> None:
        """Run shutdown callbacks."""
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
        """Create request context."""
        
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
        """Clean up request tracking."""
        self._active_requests.pop(request_id, None)
    
    async def cancel_request(self, request_id: str) -> None:
        """Cancel active request."""
        if request_id in self._active_requests:
            self._active_requests[request_id].cancel()
            logger.info(f"Cancelled request {request_id}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle incoming MCP request.
        
        This is the main dispatch point that routes requests to appropriate handlers.
        Returns None for notifications (no response expected).
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
            if method == "tools/list":
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
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        
        except Exception as e:
            logger.error(f"Error handling request {request_id}: {e}")
            return {
                "jsonrpc": "2.0", 
                "id": request_id,
                "error": {
                    "code": -32603,  # Internal error
                    "message": str(e)
                }
            }
        
        finally:
            if request_id:
                self.finish_request(request_id)
    
    async def _handle_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Handle notification messages (no response expected)."""
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
    version: str = "0.3.2", 
    description: str = "R-based statistical analysis MCP server",
) -> MCPServer:
    """Create and return a new MCP server instance."""
    return MCPServer(name=name, version=version, description=description)