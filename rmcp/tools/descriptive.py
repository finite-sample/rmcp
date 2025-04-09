# rmcp/tools/descriptive.py

from typing import Dict, Any
from rmcp.tools import mcp
from rmcp.tools.common import execute_r_script

DESCRIPTIVE_STATS_SCRIPT = """
# Compute descriptive statistics.
data <- as.data.frame(args$data)
desc_output <- capture.output(summary(data))
result <- list(summary = desc_output)
"""

@mcp.tool(
    name="descriptive_stats",
    description="Compute basic descriptive statistics for numeric columns.",
    input_schema={
        "type": "object",
        "properties": {
            "data": {"type": "object", "description": "Dataset as a dictionary/JSON object"}
        },
        "required": ["data"]
    }
)
def descriptive_stats(data: Dict[str, Any]) -> Dict[str, Any]:
    args = {"data": data}
    return execute_r_script(DESCRIPTIVE_STATS_SCRIPT, args)

