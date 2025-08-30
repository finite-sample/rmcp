"""
Registry system for MCP server capabilities.

The registry pattern provides clean separation between:
- Protocol concerns (MCP message handling)  
- Registry concerns (capability discovery and dispatch)
- Domain concerns (actual tool/resource/prompt logic)

This enables:
- Independent testing of domain logic
- Clean capability declaration
- Type-safe interfaces
"""

from .tools import ToolsRegistry, tool
from .resources import ResourcesRegistry, resource  
from .prompts import PromptsRegistry, prompt

__all__ = [
    "ToolsRegistry",
    "ResourcesRegistry", 
    "PromptsRegistry",
    "tool",
    "resource",
    "prompt",
]