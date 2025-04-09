# rmcp/tools/groupby.py

from typing import Dict, Any
from rmcp.tools.mcp_instance import mcp
from rmcp.tools.common import execute_r_script

GROUP_BY_SCRIPT = """
library(dplyr)
data <- as.data.frame(args$data)
group_col <- args$group_col
summarise_col <- args$summarise_col
stat_fun <- args$stat %||% "mean"

grouped <- data %>%
  group_by_at(vars(group_col)) %>%
  summarise(s_value = match.fun(stat_fun)(.data[[summarise_col]], na.rm = TRUE))

result <- list(summary = grouped)
"""

@mcp.tool(
    name="group_by",
    description="Group data by a column and compute a summary statistic using dplyr.",
    input_schema={
        "type": "object",
        "properties": {
            "data": {"type": "object", "description": "Dataset as a dictionary/JSON object."},
            "group_col": {"type": "string", "description": "Column name to group by."},
            "summarise_col": {"type": "string", "description": "Column name to summarise."},
            "stat": {"type": "string", "description": "Summary function (default is 'mean')."}
        },
        "required": ["data", "group_col", "summarise_col"]
    }
)
def group_by(data: Dict[str, Any], group_col: str, summarise_col: str, stat: str = "mean") -> Dict[str, Any]:
    args = {"data": data, "group_col": group_col, "summarise_col": summarise_col, "stat": stat}
    return execute_r_script(GROUP_BY_SCRIPT, args)
