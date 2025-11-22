"""
Typed context object for MCP requests.
The Context object provides:
- Per-request state (request ID, progress token, cancellation)
- Lifespan state (settings, caches, resources)
- Cross-cutting features (logging, progress, security)
Following the principle: "Makes cross-cutting features universal without globals."
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Self

if TYPE_CHECKING:
    from .server import MCPServer


@dataclass
class RequestState:
    """Per-request state passed to tool handlers."""

    request_id: str
    method: str
    progress_token: str | None = None
    tool_invocation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False

    def is_cancelled(self) -> bool:
        """Check if request has been cancelled."""
        return self.cancelled

    def cancel(self) -> None:
        """Mark request as cancelled."""
        self.cancelled = True


@dataclass
class LifespanState:
    """Lifespan state shared across requests."""

    # Configuration
    settings: dict[str, Any] = field(default_factory=dict)
    # Security
    allowed_paths: list[Path] = field(default_factory=list)
    read_only: bool = True
    # Caching
    cache_root: Path | None = None
    content_cache: dict[str, Any] = field(default_factory=dict)
    # Resources
    resource_mounts: dict[str, Path] = field(default_factory=dict)
    # Virtual File System (for security isolation)
    vfs: Any | None = None
    # Logging
    current_log_level: str = "info"
    # R Session Management
    r_session_enabled: bool = False
    r_session_timeout: float = 3600.0  # 1 hour default
    default_r_session_id: str | None = None


@dataclass
class Context:
    """
    Typed context passed to all tool handlers.
    Provides both per-request state and shared lifespan state,
    plus helpers for logging, progress, and cancellation.
    """

    request: RequestState
    lifespan: LifespanState
    # Progress/logging callbacks
    _progress_callback: Callable[[str, int, int], Awaitable[None]] | None = None
    _log_callback: Callable[[str, str, dict[str, Any]], Awaitable[None]] | None = None
    # Server reference for accessing resources
    _server: Optional["MCPServer"] = None

    @classmethod
    def create(
        cls,
        request_id: str,
        method: str,
        lifespan_state: LifespanState,
        progress_token: str | None = None,
        tool_invocation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        progress_callback: Callable[[str, int, int], Awaitable[None]] | None = None,
        log_callback: Callable[[str, str, dict[str, Any]], Awaitable[None]]
        | None = None,
    ) -> Self:
        """Create a new context for a request."""
        request_state = RequestState(
            request_id=request_id,
            method=method,
            progress_token=progress_token,
            tool_invocation_id=tool_invocation_id,
            metadata=metadata or {},
        )
        return cls(
            request=request_state,
            lifespan=lifespan_state,
            _progress_callback=progress_callback,
            _log_callback=log_callback,
        )

    # Cross-cutting feature helpers
    async def progress(self, message: str, current: int, total: int) -> None:
        """Send progress notification if progress token is available."""
        if self.request.progress_token and self._progress_callback:
            await self._progress_callback(message, current, total)

    async def log(self, level: str, message: str, **kwargs: Any) -> None:
        """Send structured log notification."""
        if self._log_callback:
            await self._log_callback(level, message, kwargs)

    async def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        await self.log("info", message, **kwargs)

    async def warn(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        await self.log("warning", message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        await self.log("error", message, **kwargs)

    def check_cancellation(self) -> None:
        """Check if request has been cancelled, raise if so."""
        if self.request.is_cancelled():
            raise asyncio.CancelledError("Request was cancelled")

    # Security helpers
    def is_path_allowed(self, path: Path) -> bool:
        """Check if path access is allowed."""
        try:
            resolved_path = path.resolve()
            return any(
                resolved_path.is_relative_to(allowed_root.resolve())
                for allowed_root in self.lifespan.allowed_paths
            )
        except (OSError, ValueError):
            return False

    def require_path_access(self, path: Path) -> None:
        """Require path access, raise if denied."""
        if not self.is_path_allowed(path):
            raise PermissionError(
                f"Path access denied: {path}. "
                f"Allowed roots: {[str(p) for p in self.lifespan.allowed_paths]}"
            )

    def get_cache_path(self, key: str) -> Path | None:
        """Get cache path for key if caching is enabled."""
        if self.lifespan.cache_root:
            return self.lifespan.cache_root / key
        return None

    # R Session Management helpers
    def is_r_session_enabled(self) -> bool:
        """Check if R session management is enabled."""
        return self.lifespan.r_session_enabled

    def get_r_session_id(self) -> str | None:
        """Get the R session ID for this context."""
        # Check for session ID in request metadata first
        session_id = self.request.metadata.get("r_session_id")
        if session_id:
            return session_id

        # Fall back to lifespan default
        return self.lifespan.default_r_session_id

    def set_r_session_id(self, session_id: str) -> None:
        """Set the R session ID for this context."""
        self.request.metadata["r_session_id"] = session_id

    async def get_or_create_r_session(
        self, working_directory: Path | None = None
    ) -> str | None:
        """Get or create an R session for this context."""
        if not self.is_r_session_enabled():
            return None

        try:
            # Import here to avoid circular imports
            from ..r_session import get_session_manager

            session_manager = get_session_manager()
            session_id = await session_manager.get_or_create_session(
                context=self,
                session_id=self.get_r_session_id(),
                working_directory=working_directory,
            )

            # Update context with session ID
            self.set_r_session_id(session_id)
            return session_id

        except Exception as e:
            await self.warn(f"Failed to get/create R session: {e}")
            return None

    async def execute_r_with_session(
        self, script: str, args: dict[str, Any], use_session: bool = True
    ) -> dict[str, Any]:
        """
        Execute R script with optional session support.

        Args:
            script: R script to execute
            args: Arguments to pass to script
            use_session: Whether to use session (if available) or run statelessly

        Returns:
            Script execution results
        """
        # Try session execution first if enabled and requested
        if use_session and self.is_r_session_enabled():
            try:
                from ..r_session import get_session_manager

                session_id = await self.get_or_create_r_session()
                if session_id:
                    session_manager = get_session_manager()
                    return await session_manager.execute_in_session(
                        session_id, script, args, self
                    )
            except Exception as e:
                await self.warn(
                    f"Session execution failed, falling back to stateless: {e}"
                )

        # Fall back to stateless execution
        from ..r_integration import execute_r_script_async

        return await execute_r_script_async(script, args, self)
