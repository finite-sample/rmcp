"""
RMCP MCP Server - A Model Context Protocol server for R-based statistical analysis.
This package implements a production-ready MCP server following established patterns:
- Spec correctness by construction using official SDK
- Clean separation of concerns (protocol/registries/domain)
- Security by default (VFS, allowlists, sandboxing)
- Transport-agnostic design (stdio primary, HTTP optional)
- Explicit schemas and typed context objects
"""

from .core.context import Context
from .core.server import create_server
from .registries.prompts import PromptsRegistry, prompt
from .registries.resources import ResourcesRegistry, resource
from .registries.tools import ToolsRegistry, tool

try:
    from importlib.metadata import version, PackageNotFoundError

    try:
        __version__ = version("rmcp")
    except PackageNotFoundError:
        # Package is not installed - fallback for development
        __version__ = "0.0.0+unknown"
except ImportError:
    # Should not happen with Python >=3.10, but keeping as safety
    __version__ = "0.0.0+unknown"
__author__ = "Gaurav Sood"
__email__ = "gsood07@gmail.com"
__all__ = [
    "Context",
    "create_server",
    "ToolsRegistry",
    "ResourcesRegistry",
    "PromptsRegistry",
    "tool",
    "resource",
    "prompt",
]
