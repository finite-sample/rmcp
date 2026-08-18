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
import ntpath
import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

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
        # Directories the user has explicitly approved for writing. These widen
        # write access within the sandbox without lifting read_only globally.
        self.writable_roots: set[Path] = set()
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
            f"read_only={self.read_only}, max_size={self.max_file_size}"
        )

    def grant_write(self, directory: str | Path) -> Path:
        """Approve writes under ``directory`` without lifting read-only globally.

        The directory must already resolve inside an allowed root, so a grant
        can widen write access within the sandbox but never escape it.
        """
        resolved = self._resolve_and_validate_path(directory)
        self.writable_roots.add(resolved)
        logger.info(f"VFS write access granted: {resolved}")
        return resolved

    def validate_write_path(self, path: str | Path) -> Path:
        """Resolve and authorize a write target without requiring it to exist.

        Tools that delegate the actual write to R must call this *before*
        handing the path over: once the subprocess starts, Python has no say in
        where it writes.
        """
        resolved = self._resolve_and_validate_path(path)
        if not self._is_writable(resolved):
            raise VFSError(
                f"Write access denied: {resolved}. The VFS is read-only; "
                "approve the directory with approve_operation to enable writing."
            )
        return resolved

    def validate_read_path(self, path: str | Path) -> Path:
        """Resolve and authorize a local file before another process reads it."""
        if str(path).lower().startswith(("http://", "https://")):
            raise VFSError(
                "Remote URL access is not permitted by the VFS; download the file "
                "to an allowed root first"
            )
        resolved = self._resolve_and_validate_path(path)
        self._check_file_constraints(resolved)
        return resolved

    @contextmanager
    def stage_read_file(self, path: str | Path) -> Iterator[Path]:
        """Yield a private snapshot of an authorized file for a subprocess.

        POSIX paths are opened component-by-component without following
        symlinks. Windows paths are authorized from the final kernel-resolved
        handle. The subprocess receives only the snapshot, so later renames or
        path swaps cannot redirect its read outside the VFS.
        """
        if str(path).lower().startswith(("http://", "https://")):
            raise VFSError(
                "Remote URL access is not permitted by the VFS; download the file "
                "to an allowed root first"
            )

        requested_suffix = Path(path).suffix
        resolved = self._resolve_and_validate_path(path)
        self._check_mime_type(resolved)
        descriptors: list[int] = []
        staged_path: Path | None = None
        try:
            if os.name == "nt":
                file_fd = os.open(
                    resolved,
                    os.O_RDONLY
                    | getattr(os, "O_BINARY", 0)
                    | getattr(os, "O_NOINHERIT", 0),
                )
                descriptors.append(file_fd)
                final_path = self._windows_final_path(file_fd)
                if not self._windows_path_is_allowed(final_path):
                    raise VFSError(f"Path access denied: {final_path}")
                self._check_mime_type(Path(final_path))
            else:
                root = next(
                    allowed_root
                    for allowed_root in self.allowed_roots
                    if resolved == allowed_root or allowed_root in resolved.parents
                )
                relative = resolved.relative_to(root)
                if not relative.parts:
                    raise VFSError(f"Not a regular file: {resolved}")

                directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                no_follow = getattr(os, "O_NOFOLLOW", 0)
                directory_fd = os.open(root, directory_flags | no_follow)
                descriptors.append(directory_fd)
                for part in relative.parts[:-1]:
                    directory_fd = os.open(
                        part,
                        directory_flags | no_follow,
                        dir_fd=directory_fd,
                    )
                    descriptors.append(directory_fd)

                file_fd = os.open(
                    relative.parts[-1], os.O_RDONLY | no_follow, dir_fd=directory_fd
                )
                descriptors.append(file_fd)

            file_stat = os.fstat(file_fd)
            if not stat.S_ISREG(file_stat.st_mode):
                raise VFSError(f"Not a regular file: {resolved}")
            if file_stat.st_size > self.max_file_size:
                raise VFSError(
                    f"File too large: {resolved} "
                    f"({file_stat.st_size} bytes, max {self.max_file_size})"
                )

            with tempfile.NamedTemporaryFile(
                prefix="rmcp-read-", suffix=requested_suffix, delete=False
            ) as staged:
                staged_path = Path(staged.name)
                with os.fdopen(os.dup(file_fd), "rb") as source:
                    copied = 0
                    while chunk := source.read(
                        min(1024 * 1024, self.max_file_size + 1)
                    ):
                        copied += len(chunk)
                        if copied > self.max_file_size:
                            raise VFSError(
                                f"File too large: {resolved} "
                                f"(more than {self.max_file_size} bytes)"
                            )
                        staged.write(chunk)

            assert staged_path is not None
            os.utime(
                staged_path,
                ns=(file_stat.st_atime_ns, file_stat.st_mtime_ns),
            )

            yield staged_path
        except OSError as exc:
            raise VFSError(f"Failed to stage file {resolved}: {exc}") from exc
        finally:
            for descriptor in reversed(descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if staged_path is not None:
                try:
                    staged_path.unlink()
                except OSError:
                    pass

    @staticmethod
    def _normalize_windows_final_path(path: str) -> str:
        """Convert a Win32 final-handle path to a normal DOS or UNC path."""
        if path.startswith("\\\\?\\UNC\\"):
            return "\\\\" + path[8:]
        if path.startswith("\\\\?\\"):
            return path[4:]
        return path

    def _windows_path_is_allowed(self, path: str) -> bool:
        """Check a handle-resolved Windows path against configured roots."""
        candidate = ntpath.normcase(ntpath.normpath(path))
        for allowed_root in self.allowed_roots:
            root = ntpath.normcase(ntpath.normpath(str(allowed_root)))
            try:
                if ntpath.commonpath((candidate, root)) == root:
                    return True
            except ValueError:
                continue
        return False

    @classmethod
    def _windows_final_path(cls, file_descriptor: int) -> str:
        """Return the kernel-resolved path for an open Windows file."""
        import ctypes
        import msvcrt
        from ctypes import wintypes

        ctypes_windows = cast(Any, ctypes)
        msvcrt_windows = cast(Any, msvcrt)
        get_final_path = ctypes_windows.WinDLL(
            "kernel32", use_last_error=True
        ).GetFinalPathNameByHandleW
        get_final_path.argtypes = (
            wintypes.HANDLE,
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
        )
        get_final_path.restype = wintypes.DWORD
        handle = wintypes.HANDLE(msvcrt_windows.get_osfhandle(file_descriptor))
        size = 32768
        while True:
            buffer = ctypes.create_unicode_buffer(size)
            length = get_final_path(handle, buffer, size, 0)
            if length == 0:
                error_code = ctypes_windows.get_last_error()
                message = ctypes_windows.FormatError(error_code)
                raise OSError(error_code, message)
            if length < size:
                return cls._normalize_windows_final_path(buffer.value)
            size = length + 1

    def _is_writable(self, path: Path) -> bool:
        """Whether ``path`` may be written, honoring per-directory grants."""
        if not self.read_only:
            return True
        return any(path == root or root in path.parents for root in self.writable_roots)

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
        self._check_mime_type(path)

    def _check_mime_type(self, path: Path) -> None:
        """Check a path's declared file type against the allowlist."""
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
        resolved_path = self._resolve_and_validate_path(path)
        if not self._is_writable(resolved_path):
            raise VFSError("VFS is configured as read-only")
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

        resolved_path = self._resolve_and_validate_path(path)
        if not self._is_writable(resolved_path):
            raise VFSError("VFS is configured as read-only")
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
                "writable": os.access(resolved_path, os.W_OK)
                and self._is_writable(resolved_path),
            }
        except OSError as e:
            raise VFSError(f"Failed to get file info for {resolved_path}: {e}")
