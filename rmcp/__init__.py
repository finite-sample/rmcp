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
from .version import get_version

__version__ = get_version()
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
