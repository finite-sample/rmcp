from rmcp.server.fastmcp import FastMCP

# Central MCP instance
mcp = FastMCP(
    name="R Econometrics",
    version="0.1.0",
    description="A Model Context Protocol server for R-based econometric analysis"
)

# Import all tools
from .regression import linear_model, panel_model, iv_regression
from .diagnostics import diagnostics
from .correlation import correlation
from .groupby import group_by
from .file_analysis import analyze_csv
from .prompts import panel_data_analysis_prompt

# Explicitly export tools
__all__ = [
    'mcp',
    'linear_model', 
    'panel_model', 
    'iv_regression', 
    'diagnostics', 
    'correlation', 
    'group_by', 
    'analyze_csv', 
    'panel_data_analysis_prompt'
]

# Optional: Register tools with the MCP instance
mcp.register_tool(name="linear_model", func=linear_model)
mcp.register_tool(name="panel_model", func=panel_model)
mcp.register_tool(name="iv_regression", func=iv_regression)
mcp.register_tool(name="diagnostics", func=diagnostics)
mcp.register_tool(name="correlation", func=correlation)
mcp.register_tool(name="group_by", func=group_by)
mcp.register_tool(name="analyze_csv", func=analyze_csv)
mcp.register_tool(name="panel_data_analysis_prompt", func=panel_data_analysis_prompt)