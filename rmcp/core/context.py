"""
Typed context object for MCP requests.
The Context object provides:
- Per-request state (request ID, progress token, cancellation)
- Lifespan state (settings, caches, resources)
- Cross-cutting features (logging, progress, security)
Following the principle: "Makes cross-cutting features universal without globals."
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional


@dataclass
class RequestState:
    """Per-request state passed to tool handlers."""

    request_id: str
    method: str
    progress_token: Optional[str] = None
    tool_invocation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
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
    settings: Dict[str, Any] = field(default_factory=dict)
    # Security
    allowed_paths: list[Path] = field(default_factory=list)
    read_only: bool = True
    # Caching
    cache_root: Optional[Path] = None
    content_cache: Dict[str, Any] = field(default_factory=dict)
    # Resources
    resource_mounts: Dict[str, Path] = field(default_factory=dict)
    # Virtual File System (for security isolation)
    vfs: Optional[Any] = None
    # Logging
    current_log_level: str = "info"


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
    _progress_callback: Optional[Callable[[str, int, int], Awaitable[None]]] = None
    _log_callback: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[None]]] = (
        None
    )

    @classmethod
    def create(
        cls,
        request_id: str,
        method: str,
        lifespan_state: LifespanState,
        progress_token: Optional[str] = None,
        tool_invocation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, int, int], Awaitable[None]]] = None,
        log_callback: Optional[
            Callable[[str, str, Dict[str, Any]], Awaitable[None]]
        ] = None,
    ) -> "Context":
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

    def get_cache_path(self, key: str) -> Optional[Path]:
        """Get cache path for key if caching is enabled."""
        if self.lifespan.cache_root:
            return self.lifespan.cache_root / key
        return None
