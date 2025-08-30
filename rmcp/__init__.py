"""
RMCP - R Model Context Protocol

A Model Context Protocol (MCP) server that provides advanced econometric
modeling and data analysis capabilities through R.
"""

__version__ = "0.1.1"
__author__ = "Gaurav Sood"
__email__ = "gsood07@gmail.com"
__description__ = "A Model Context Protocol server for R"

from rmcp.tools import mcp

__all__ = ["mcp", "__version__"]