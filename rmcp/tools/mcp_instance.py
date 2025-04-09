# rmcp/tools/mcp_instance.py

from rmcp.server.fastmcp import FastMCP

# Central MCP instance
mcp = FastMCP(
    name="R Econometrics",
    version="0.1.0",
    description="A Model Context Protocol server for R-based econometric analysis"
)
