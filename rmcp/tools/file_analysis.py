# rmcp/tools/file_analysis.py

from typing import Dict, Any
from rmcp.tools.mcp_instance import mcp
from rmcp.tools.common import execute_r_script

FILE_ANALYSIS_SCRIPT = """
# Load and analyze a CSV file.
data <- read.csv(args$file_path, stringsAsFactors = FALSE)
# Compute descriptive statistics.
desc_output <- capture.output(summary(data))
result <- list(
  summary = desc_output,
  colnames = colnames(data),
  nrows = nrow(data),
  ncols = ncol(data)
)
"""

@mcp.tool(
    name="analyze_csv",
    description="Load and analyze a CSV file, returning summary statistics, column names, and dimensions.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path (relative or absolute) to the CSV file to analyze."
            }
        },
        "required": ["file_path"]
    }
)
def analyze_csv(file_path: str) -> Dict[str, Any]:
    args = {"file_path": file_path}
    return execute_r_script(FILE_ANALYSIS_SCRIPT, args)
