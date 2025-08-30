"""
Transport layer for MCP server.

Implements transport-agnostic message handling:
- stdio transport (JSON-RPC over stdin/stdout) 
- Optional HTTP transport with streaming support
- Clean separation from business logic

Following the principle: "Business logic never cares whether messages arrive over stdio or HTTP."
"""

from .stdio import StdioTransport
from .jsonrpc import JSONRPCEnvelope, JSONRPCError
from .base import Transport

__all__ = ["StdioTransport", "JSONRPCEnvelope", "JSONRPCError", "Transport"]