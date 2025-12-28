"""
Virtual File System for secure file access.
Implements mature MCP server patterns:
- Explicit allowed roots (mounts)
- Path normalization and traversal checks
- MIME type detection and size caps
- Read-only enforcement
Following the pattern: "Gate filesystem access with a tiny VFS."
"""

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

from ..config import get_config

logger = logging.getLogger(__name__)


class VFSError(Exception):
    """VFS access error."""

    pass


class VFS:
    """
    Virtual File System with security controls.
    Provides safe file access with:
    - Allowlisted root directories (explicit mounts)
    - Path traversal protection
    - File type and size limits
    - Read-only enforcement
    """

    def __init__(
        self,
        allowed_roots: list[Path],
        read_only: bool | None = None,
        max_file_size: int | None = None,
        allowed_mime_types: list[str] | None = None,
    ):
        self.allowed_roots = [root.resolve() for root in allowed_roots]

        # Use configuration defaults if not provided
        config = get_config()
        self.read_only = (
            read_only if read_only is not None else config.security.vfs_read_only
        )
        self.max_file_size = (
            max_file_size
            if max_file_size is not None
            else config.security.vfs_max_file_size
        )
        # Default allowed MIME types for data analysis
        self.allowed_mime_types = (
            allowed_mime_types
            or config.security.vfs_allowed_mime_types
            or [
                "text/plain",
                "text/csv",
                "application/json",
                "application/xml",
                "text/xml",
                "application/pdf",
                "text/tab-separated-values",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                # Image types for visualization output
                "image/png",
                "image/jpeg",
                "image/jpg",
                "image/svg+xml",
                "image/pdf",
            ]
        )
        logger.info(
            f"VFS initialized: {len(self.allowed_roots)} roots, "
            f"read_only={read_only}, max_size={max_file_size}"
        )

    def _resolve_and_validate_path(self, path: str | Path) -> Path:
        """Resolve path and validate against allowed roots."""
        try:
            # Resolve path to handle symlinks and relative paths
            resolved_path = Path(path).resolve()
        except (OSError, ValueError) as e:
            raise VFSError(f"Invalid path: {path} ({e})")
        # Check if path is under any allowed root
        for allowed_root in self.allowed_roots:
            try:
                resolved_path.relative_to(allowed_root)
                return resolved_path
            except ValueError:
                continue
        # Not under any allowed root
        allowed_roots_str = ", ".join(str(root) for root in self.allowed_roots)
        raise VFSError(
            f"Path access denied: {resolved_path}. Allowed roots: [{allowed_roots_str}]"
        )

    def _check_file_constraints(self, path: Path) -> None:
        """Check file size and type constraints."""
        if not path.exists():
            raise VFSError(f"File not found: {path}")
        if not path.is_file():
            raise VFSError(f"Not a regular file: {path}")
        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            raise VFSError(
                f"File too large: {path} ({file_size} bytes, max {self.max_file_size})"
            )
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type and mime_type not in self.allowed_mime_types:
            raise VFSError(
                f"File type not allowed: {path} ({mime_type}). "
                f"Allowed types: {self.allowed_mime_types}"
            )

    def read_file(self, path: str | Path) -> bytes:
        """Read file with security checks."""
        resolved_path = self._resolve_and_validate_path(path)
        self._check_file_constraints(resolved_path)
        try:
            with open(resolved_path, "rb") as f:
                content = f.read()
            logger.debug(f"Read file: {resolved_path} ({len(content)} bytes)")
            return content
        except OSError as e:
            raise VFSError(f"Failed to read file {resolved_path}: {e}")

    async def read_file_async(self, path: str | Path) -> bytes:
        """Read file asynchronously with security checks."""
        import asyncio

        resolved_path = self._resolve_and_validate_path(path)
        self._check_file_constraints(resolved_path)

        def _read_file():
            try:
                with open(resolved_path, "rb") as f:
                    return f.read()
            except OSError as e:
                raise VFSError(f"Failed to read file {resolved_path}: {e}")

        # Run file I/O in thread pool to avoid blocking event loop
        content = await asyncio.get_event_loop().run_in_executor(None, _read_file)
        logger.debug(f"Read file async: {resolved_path} ({len(content)} bytes)")
        return content

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        """Read text file with security checks."""
        content = self.read_file(path)
        try:
            return content.decode(encoding)
        except UnicodeDecodeError as e:
            raise VFSError(f"Failed to decode file {path} as {encoding}: {e}")

    def list_directory(self, path: str | Path) -> list[dict[str, Any]]:
        """List directory contents with security checks."""
        resolved_path = self._resolve_and_validate_path(path)
        if not resolved_path.is_dir():
            raise VFSError(f"Not a directory: {resolved_path}")
        try:
            entries = []
            for entry in resolved_path.iterdir():
                try:
                    stat = entry.stat()
                    mime_type, _ = mimetypes.guess_type(str(entry))
                    entries.append(
                        {
                            "name": entry.name,
                            "path": str(entry),
                            "type": "directory" if entry.is_dir() else "file",
                            "size": stat.st_size if entry.is_file() else None,
                            "modified": stat.st_mtime,
                            "mime_type": mime_type,
                        }
                    )
                except OSError:
                    # Skip entries we can't stat
                    continue
            logger.debug(f"Listed directory: {resolved_path} ({len(entries)} entries)")
            return entries
        except OSError as e:
            raise VFSError(f"Failed to list directory {resolved_path}: {e}")

    def write_file(self, path: str | Path, content: bytes) -> None:
        """Write file with security checks."""
        if self.read_only:
            raise VFSError("VFS is configured as read-only")
        resolved_path = self._resolve_and_validate_path(path)
        # Check content size
        if len(content) > self.max_file_size:
            raise VFSError(
                f"Content too large: {len(content)} bytes, max {self.max_file_size}"
            )
        try:
            # Ensure parent directory exists
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            with open(resolved_path, "wb") as f:
                f.write(content)
            logger.debug(f"Wrote file: {resolved_path} ({len(content)} bytes)")
        except OSError as e:
            raise VFSError(f"Failed to write file {resolved_path}: {e}")

    async def write_file_async(self, path: str | Path, content: bytes) -> None:
        """Write file asynchronously with security checks."""
        import asyncio

        if self.read_only:
            raise VFSError("VFS is configured as read-only")
        resolved_path = self._resolve_and_validate_path(path)
        # Check content size
        if len(content) > self.max_file_size:
            raise VFSError(
                f"Content too large: {len(content)} bytes, max {self.max_file_size}"
            )

        def _write_file():
            try:
                # Ensure parent directory exists
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
                with open(resolved_path, "wb") as f:
                    f.write(content)
            except OSError as e:
                raise VFSError(f"Failed to write file {resolved_path}: {e}")

        # Run file I/O in thread pool to avoid blocking event loop
        await asyncio.get_event_loop().run_in_executor(None, _write_file)
        logger.debug(f"Wrote file async: {resolved_path} ({len(content)} bytes)")

    def write_text(
        self, path: str | Path, content: str, encoding: str = "utf-8"
    ) -> None:
        """Write text file with security checks."""
        try:
            encoded_content = content.encode(encoding)
            self.write_file(path, encoded_content)
        except UnicodeEncodeError as e:
            raise VFSError(f"Failed to encode content as {encoding}: {e}")

    def file_info(self, path: str | Path) -> dict[str, Any]:
        """Get file information with security checks."""
        resolved_path = self._resolve_and_validate_path(path)
        if not resolved_path.exists():
            raise VFSError(f"File not found: {resolved_path}")
        try:
            stat = resolved_path.stat()
            mime_type, encoding = mimetypes.guess_type(str(resolved_path))
            return {
                "path": str(resolved_path),
                "name": resolved_path.name,
                "type": "directory" if resolved_path.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "mime_type": mime_type,
                "encoding": encoding,
                "readable": os.access(resolved_path, os.R_OK),
                "writable": os.access(resolved_path, os.W_OK) and not self.read_only,
            }
        except OSError as e:
            raise VFSError(f"Failed to get file info for {resolved_path}: {e}")
