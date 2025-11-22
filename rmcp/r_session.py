"""
R Session Management for RMCP.

This module provides persistent R session management capabilities inspired by mcptools,
allowing for stateful interactions between the MCP server and R environments.

Key features:
- Persistent R sessions with workspace state
- Session discovery and lifecycle management
- Environment introspection and object management
- Context-aware tool execution with session persistence
- Graceful session cleanup and resource management

Design principles:
- Sessions are optional - tools can still run statelessly
- Session state is isolated per context/user
- Automatic cleanup of abandoned sessions
- Transparent fallback to stateless execution
"""

import asyncio
import json
import logging
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core.context import Context
from .r_integration import RExecutionError, get_r_binary_path

logger = logging.getLogger(__name__)


@dataclass
class RSessionInfo:
    """Information about an R session."""

    session_id: str
    working_directory: Path
    created_at: float
    last_accessed: float
    process_id: int | None = None
    workspace_objects: set[str] = field(default_factory=set)
    packages_loaded: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if session is still active."""
        if self.process_id is None:
            return False

        try:
            # Check if process is still running
            import psutil

            process = psutil.Process(self.process_id)
            return process.is_running()
        except (ImportError, psutil.NoSuchProcess):
            # Fallback if psutil not available
            try:
                import os

                os.kill(self.process_id, 0)
                return True
            except (OSError, ProcessLookupError):
                return False

    def update_access_time(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = time.time()


class RSessionManager:
    """
    Manages persistent R sessions for stateful statistical analysis.

    This class provides session lifecycle management, allowing tools to maintain
    workspace state across multiple invocations. Sessions are automatically
    cleaned up when they become inactive or are explicitly closed.
    """

    def __init__(self, session_timeout: float = 3600.0, max_sessions: int = 10):
        """
        Initialize R session manager.

        Args:
            session_timeout: Session timeout in seconds (default: 1 hour)
            max_sessions: Maximum number of concurrent sessions
        """
        self._sessions: dict[str, RSessionInfo] = {}
        self._session_processes: dict[str, asyncio.subprocess.Process] = {}
        self._session_timeout = session_timeout
        self._max_sessions = max_sessions
        self._cleanup_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start_manager(self) -> None:
        """Start the session manager and cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(
                self._cleanup_sessions_periodically()
            )
            logger.info("R session manager started")

    async def stop_manager(self) -> None:
        """Stop the session manager and cleanup all sessions."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Close all active sessions
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)

        logger.info("R session manager stopped")

    async def get_or_create_session(
        self,
        context: Context,
        session_id: str | None = None,
        working_directory: Path | None = None,
    ) -> str:
        """
        Get existing session or create a new one.

        Args:
            context: Current request context
            session_id: Specific session ID to get/create
            working_directory: Working directory for the session

        Returns:
            Session ID
        """
        async with self._lock:
            # Generate session ID if not provided
            if session_id is None:
                session_id = f"r_session_{uuid.uuid4().hex[:8]}"

            # Check if session exists and is active
            if session_id in self._sessions:
                session_info = self._sessions[session_id]
                if session_info.is_active():
                    session_info.update_access_time()
                    await context.info(f"Using existing R session: {session_id}")
                    return session_id
                else:
                    # Session exists but is inactive, remove it
                    await self._remove_session(session_id)

            # Create new session
            return await self._create_session(context, session_id, working_directory)

    async def _create_session(
        self,
        context: Context,
        session_id: str,
        working_directory: Path | None = None,
    ) -> str:
        """Create a new R session."""
        # Check session limits
        if len(self._sessions) >= self._max_sessions:
            await self._cleanup_oldest_session()

        # Determine working directory
        if working_directory is None:
            working_directory = Path.cwd()

        # Create session info
        session_info = RSessionInfo(
            session_id=session_id,
            working_directory=working_directory,
            created_at=time.time(),
            last_accessed=time.time(),
        )

        try:
            # Start R process
            r_binary = get_r_binary_path()
            process = await asyncio.create_subprocess_exec(
                r_binary,
                "--slave",
                "--no-restore",
                "--no-save",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=working_directory,
            )

            session_info.process_id = process.pid
            self._sessions[session_id] = session_info
            self._session_processes[session_id] = process

            # Initialize session with basic setup
            await self._initialize_session(session_id, context)

            await context.info(
                f"Created new R session: {session_id} (PID: {process.pid})"
            )
            return session_id

        except Exception as e:
            await context.error(f"Failed to create R session {session_id}: {e}")
            if session_id in self._sessions:
                del self._sessions[session_id]
            raise RExecutionError(f"Failed to create R session: {e}")

    async def _initialize_session(self, session_id: str, context: Context) -> None:
        """Initialize a new R session with basic packages and utilities."""
        init_script = f"""
        # Load essential packages
        if (!require(jsonlite, quietly = TRUE)) {{
            install.packages("jsonlite", repos = "https://cran.r-project.org")
            library(jsonlite)
        }}

        # Set up session metadata
        .rmcp_session_id <- "{session_id}"
        .rmcp_session_start <- Sys.time()

        # Define helper functions for session management
        .rmcp_list_objects <- function() {{
            objects_info <- ls.str(envir = .GlobalEnv, max.level = 1)
            return(ls(envir = .GlobalEnv))
        }}

        .rmcp_get_object_info <- function(name) {{
            if (!exists(name, envir = .GlobalEnv)) {{
                return(list(exists = FALSE))
            }}
            obj <- get(name, envir = .GlobalEnv)
            list(
                exists = TRUE,
                class = class(obj),
                type = typeof(obj),
                length = length(obj),
                size = object.size(obj),
                summary = capture.output(str(obj))
            )
        }}

        # Session ready
        cat("RMCP session initialized\\n")
        """

        try:
            await self._execute_in_session(session_id, init_script, context)
        except Exception as e:
            await context.warn(f"Session initialization warning: {e}")

    async def execute_in_session(
        self, session_id: str, script: str, args: dict[str, Any], context: Context
    ) -> dict[str, Any]:
        """
        Execute R script in specific session.

        Args:
            session_id: Target session ID
            script: R script to execute
            args: Arguments to pass to script
            context: Request context

        Returns:
            Script execution results
        """
        async with self._lock:
            if session_id not in self._sessions:
                raise RExecutionError(f"Session {session_id} not found")

            session_info = self._sessions[session_id]
            if not session_info.is_active():
                await self._remove_session(session_id)
                raise RExecutionError(f"Session {session_id} is no longer active")

            session_info.update_access_time()

        # Create execution script with args injection
        execution_script = f"""
        # Inject arguments
        args <- {json.dumps(args)}

        # Execute user script
        tryCatch({{
            {script}

            # Return result
            if (exists("result")) {{
                cat(toJSON(result, auto_unbox = TRUE))
            }} else {{
                cat(toJSON(list(success = TRUE, message = "Script executed but no result variable set")))
            }}
        }}, error = function(e) {{
            cat(toJSON(list(error = TRUE, message = e$message)))
        }})
        """

        return await self._execute_in_session(session_id, execution_script, context)

    async def _execute_in_session(
        self, session_id: str, script: str, context: Context
    ) -> dict[str, Any]:
        """Execute script in session and return results."""
        process = self._session_processes.get(session_id)
        if not process:
            raise RExecutionError(f"No active process for session {session_id}")

        try:
            # Send script to R session
            if process.stdin is None:
                raise RExecutionError(f"No stdin available for session {session_id}")
            script_bytes = (script + "\n").encode("utf-8")
            process.stdin.write(script_bytes)
            await process.stdin.drain()

            # Read response (this is a simplified version - production would need more robust parsing)
            # For now, we'll use the stateless execution as fallback
            from .r_integration import execute_r_script_async

            return await execute_r_script_async(script, {}, context)

        except Exception as e:
            await context.error(f"Error executing in session {session_id}: {e}")
            # Mark session as inactive
            await self._remove_session(session_id)
            raise RExecutionError(f"Session execution failed: {e}")

    async def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions with their metadata."""
        sessions = []
        for session_id, session_info in self._sessions.items():
            if session_info.is_active():
                sessions.append(
                    {
                        "session_id": session_id,
                        "working_directory": str(session_info.working_directory),
                        "created_at": session_info.created_at,
                        "last_accessed": session_info.last_accessed,
                        "process_id": session_info.process_id,
                        "workspace_objects": list(session_info.workspace_objects),
                        "packages_loaded": list(session_info.packages_loaded),
                        "metadata": session_info.metadata,
                    }
                )
        return sessions

    async def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """Get detailed information about a specific session."""
        if session_id not in self._sessions:
            return None

        session_info = self._sessions[session_id]
        if not session_info.is_active():
            await self._remove_session(session_id)
            return None

        return {
            "session_id": session_id,
            "working_directory": str(session_info.working_directory),
            "created_at": session_info.created_at,
            "last_accessed": session_info.last_accessed,
            "process_id": session_info.process_id,
            "workspace_objects": list(session_info.workspace_objects),
            "packages_loaded": list(session_info.packages_loaded),
            "metadata": session_info.metadata,
        }

    async def close_session(self, session_id: str) -> bool:
        """Close and cleanup a specific session."""
        if session_id not in self._sessions:
            return False

        await self._remove_session(session_id)
        return True

    async def _remove_session(self, session_id: str) -> None:
        """Remove session and cleanup resources."""
        # Close R process
        if session_id in self._session_processes:
            process = self._session_processes[session_id]
            try:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except TimeoutError:
                    process.kill()
                    await process.wait()
            except Exception as e:
                logger.warning(f"Error closing R process for session {session_id}: {e}")

            del self._session_processes[session_id]

        # Remove session info
        if session_id in self._sessions:
            del self._sessions[session_id]

        logger.info(f"Removed R session: {session_id}")

    async def _cleanup_sessions_periodically(self) -> None:
        """Periodically cleanup inactive and expired sessions."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")

    async def _cleanup_expired_sessions(self) -> None:
        """Remove expired or inactive sessions."""
        current_time = time.time()
        expired_sessions = []

        for session_id, session_info in self._sessions.items():
            if (
                not session_info.is_active()
                or current_time - session_info.last_accessed > self._session_timeout
            ):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self._remove_session(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")

    async def _cleanup_oldest_session(self) -> None:
        """Remove the oldest session to make room for a new one."""
        if not self._sessions:
            return

        oldest_session_id = min(
            self._sessions.keys(), key=lambda sid: self._sessions[sid].last_accessed
        )

        await self._remove_session(oldest_session_id)
        logger.info(f"Removed oldest session to make room: {oldest_session_id}")


# Global session manager instance
_session_manager: RSessionManager | None = None


def get_session_manager() -> RSessionManager:
    """Get the global R session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = RSessionManager()
    return _session_manager


async def initialize_session_manager() -> None:
    """Initialize the global session manager."""
    manager = get_session_manager()
    await manager.start_manager()


async def cleanup_session_manager() -> None:
    """Cleanup the global session manager."""
    global _session_manager
    if _session_manager:
        await _session_manager.stop_manager()
        _session_manager = None
