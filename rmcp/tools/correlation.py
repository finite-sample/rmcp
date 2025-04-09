# rmcp/tools/correlation.py

from typing import Dict, Any
from rmcp.tools import mcp
from rmcp.tools.common import execute_r_script

CORRELATION_SCRIPT = """
# Compute correlation between two variables.
data <- as.data.frame(args$data)
var1 <- args$var1
var2 <- args$var2
method <- args$method %||% "pearson"
corr_value <- cor(data[[var1]], data[[var2]], method = method, use = "complete.obs")
result <- list(correlation = corr_value, method = method)
"""

@mcp.tool(
    name="correlation",
    description="Compute correlation between two variables (Pearson or Spearman).",
    input_schema={
        "type": "object",
        "properties": {
            "data": {"type": "object", "description": "Dataset as a dictionary/JSON object."},
            "var1": {"type": "string", "description": "First variable name."},
            "var2": {"type": "string", "description": "Second variable name."},
            "method": {"type": "string", "description": "Correlation method ('pearson' or 'spearman')."}
        },
        "required": ["data", "var1", "var2"]
    }
)
def correlation(data: Dict[str, Any], var1: str, var2: str, method: str = "pearson") -> Dict[str, Any]:
    args = {"data": data, "var1": var1, "var2": var2, "method": method}
    return execute_r_script(CORRELATION_SCRIPT, args)
