# rmcp/tools/__init__.py

from rmcp.server.fastmcp import FastMCP

# Create the shared MCP server instance.
mcp = FastMCP(
    name="R Econometrics",
    version="0.1.0",
    description="A Model Context Protocol server for R-based econometric analysis"
)

# Import the modules to register their tools.
from .regression import linear_model, panel_model, iv_regression
from .diagnostics import diagnostics
from .descriptive import descriptive_stats
from .correlation import correlation
from .groupby import group_by

# Import prompts to make them available via the package.
from .prompts import panel_data_analysis_prompt, time_series_analysis_prompt
