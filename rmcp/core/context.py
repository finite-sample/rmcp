"""
Typed context object for MCP requests.
The Context object provides:
- Per-request state (request ID, progress token, cancellation)
- Lifespan state (settings, caches, resources)
- Cross-cutting features (logging, progress, security)
Following the principle: "Makes cross-cutting features universal without globals."
"""

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
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
    # Operation approvals granted by the user. Lives here rather than on Context
    # because a fresh Context is built per request -- approvals must outlive it.
    approved_operations: dict[str, dict[str, Any]] = field(default_factory=dict)
    approved_packages: set[str] = field(default_factory=set)


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

    def require_write_path(self, path: str | Path) -> Path | None:
        """Require permission to write ``path``, raising if denied.

        Tools that hand a path to R must call this first: the subprocess writes
        the bytes, so this is the last point Python controls the destination.

        Fails open when no VFS is configured -- absent a policy object there is
        no policy to enforce, which keeps embedders working. Both CLI entry
        points call ``MCPServer.configure()``, so servers always have one.
        """
        vfs = getattr(self.lifespan, "vfs", None)
        if vfs is None:
            return None
        return vfs.validate_write_path(path)

    def require_read_path(self, path: str | Path) -> Path | None:
        """Require permission to read ``path`` before delegating to R."""
        vfs = getattr(self.lifespan, "vfs", None)
        if vfs is None:
            return None
        return vfs.validate_read_path(path)

    @contextmanager
    def stage_read_path(self, path: str | Path) -> Iterator[Path]:
        """Yield a stable authorized path suitable for delegated reads."""
        vfs = getattr(self.lifespan, "vfs", None)
        if vfs is None:
            yield Path(path)
            return
        with vfs.stage_read_file(path) as staged_path:
            yield staged_path

    def get_cache_path(self, key: str) -> Path | None:
        """Get cache path for key if caching is enabled."""
        if self.lifespan.cache_root:
            return self.lifespan.cache_root / key
        return None

    async def execute_r(self, script: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Execute an R script.

        Args:
            script: R script to execute
            args: Arguments to pass to script

        Returns:
            Script execution results
        """
        # Import here to avoid circular imports
        from ..r_integration import execute_r_script_async

        return await execute_r_script_async(script, args, self)
