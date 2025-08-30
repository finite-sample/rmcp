"""
Type definitions for RMCP.

This module contains type aliases and data structures used throughout
the RMCP (R Model Context Protocol) server.
"""

from typing import Any, Dict, List, Union, Optional, Callable
from dataclasses import dataclass

# Type aliases for common data structures
JsonData = Dict[str, Any]
RData = Dict[str, Union[List[Union[str, int, float]], str, int, float]]
JsonSchema = Dict[str, Any]
JsonSchemaProperty = Dict[str, Any]

# MCP Protocol types
MCPMessage = Dict[str, Any]
MCPResponse = Dict[str, Any]
ToolFunction = Callable[..., JsonData]

@dataclass
class ToolInfo:
    """Information about a registered tool."""
    name: str
    function: ToolFunction
    description: str
    schema: JsonSchema

@dataclass
class ServerInfo:
    """Server configuration information."""
    name: str
    version: str
    description: str
