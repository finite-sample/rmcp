"""
Transport layer for MCP server.

Wire-level transports are provided by the official MCP SDK (see
:mod:`rmcp.transport.sdk` for stdio and Streamable HTTP runners).
:class:`Transport` remains as the abstraction used by the in-process
message-handler path (`MCPServer.create_message_handler`).
"""

from .base import Transport

__all__ = ["Transport"]
