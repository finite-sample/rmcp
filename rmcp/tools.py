# rmcp/tools.py
from rmcp.server.fastmcp import FastMCP
from rmcp.rmcp import execute_r_script  # or move execute_r_script into a shared module
# Import your R script constants too, if needed:
from rmcp.rmcp import LINEAR_REGRESSION_SCRIPT, PANEL_MODEL_SCRIPT, DIAGNOSTICS_SCRIPT, IV_REGRESSION_SCRIPT

mcp = FastMCP(
    name="R Econometrics",
    version="0.1.0",
    description="A Model Context Protocol server for R-based econometric analysis"
)

@mcp.tool(
    name="linear_model",
    description="Run a linear regression model",
    input_schema={
        "type": "object",
        "properties": {
            "formula": {"type": "string", "description": "The regression formula (e.g., 'y ~ x1 + x2')"},
            "data": {"type": "object", "description": "Dataset as a dictionary/JSON object"},
            "robust": {"type": "boolean", "description": "Whether to use robust standard errors"}
        },
        "required": ["formula", "data"]
    }
)
def linear_model(formula: str, data: dict, robust: bool = False) -> dict:
    args = {"formula": formula, "data": data, "robust": robust}
    return execute_r_script(LINEAR_REGRESSION_SCRIPT, args)

# Register additional tools similarly...

# Expose the instance for use in other modules.
__all__ = ["mcp"]
