# Import the MCP instance from its own module to avoid circular imports
from .mcp_instance import mcp

# Import all tools (this will register them with the mcp instance via decorators)
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

# Tools are automatically registered via decorators in their respective modules
# No need for manual registration as they use @mcp.tool decorator