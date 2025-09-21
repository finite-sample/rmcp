"""
Security components for MCP server.
Implements:
- Virtual File System (VFS) with allowlists and sandboxing
- Path traversal protection
- Content type validation
- Size limits and safety checks
Following the principle: "Security by default."
"""

from .vfs import VFS, VFSError

__all__ = ["VFS", "VFSError"]
