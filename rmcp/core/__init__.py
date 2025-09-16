"""
Core MCP server components.

This module contains the fundamental building blocks:
- Context: Typed context for request + lifespan state
- Server: MCP app shell with lifecycle hooks
- Schemas: JSON Schema validation helpers
"""

from .context import Context
from .server import create_server
from .schemas import validate_schema, SchemaError

__all__ = ["Context", "create_server", "validate_schema", "SchemaError"]