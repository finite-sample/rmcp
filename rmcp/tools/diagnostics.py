# rmcp/tools/diagnostics.py

from typing import Dict, Any, List
from rmcp.tools.mcp_instance import mcp
from rmcp.tools.common import execute_r_script

DIAGNOSTICS_SCRIPT = """
# Perform model diagnostics.
data <- as.data.frame(args$data)
formula <- as.formula(args$formula)
tests <- args$tests

model <- lm(formula, data = data)
results <- list()

for (test in tests) {
  if (test == "bp") {
    bp_test <- lmtest::bptest(model)
    results$bp <- list(
      statistic = as.numeric(bp_test$statistic),
      p_value = as.numeric(bp_test$p.value),
      parameter = as.numeric(bp_test$parameter),
      method = bp_test$method
    )
  } else if (test == "reset") {
    reset_test <- lmtest::resettest(model)
    results$reset <- list(
      statistic = as.numeric(reset_test$statistic),
      p_value = as.numeric(reset_test$p.value),
      parameter = as.numeric(reset_test$parameter),
      method = reset_test$method
    )
  } else if (test == "dw") {
    dw_test <- lmtest::dwtest(model)
    results$dw <- list(
      statistic = as.numeric(dw_test$statistic),
      p_value = as.numeric(dw_test$p.value),
      method = dw_test$method
    )
  }
}
result <- results
"""

@mcp.tool(
    name="diagnostics",
    description="Perform model diagnostics",
    input_schema={
        "type": "object",
        "properties": {
            "formula": {"type": "string", "description": "The regression formula (e.g., 'y ~ x1 + x2')"},
            "data": {"type": "object", "description": "Dataset as a dictionary/JSON object"},
            "tests": {"type": "array", "description": "List of tests (e.g., ['bp', 'reset', 'dw'])"}
        },
        "required": ["formula", "data", "tests"]
    }
)
def diagnostics(formula: str, data: Dict[str, Any], tests: List[str]) -> Dict[str, Any]:
    args = {"formula": formula, "data": data, "tests": tests}
    return execute_r_script(DIAGNOSTICS_SCRIPT, args)
