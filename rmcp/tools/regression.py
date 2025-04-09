# rmcp/tools/regression.py

from typing import Dict, Any, List
from rmcp.tools import mcp
from rmcp.tools.common import execute_r_script

LINEAR_REGRESSION_SCRIPT = """
# Perform linear regression.
data <- as.data.frame(args$data)
formula <- as.formula(args$formula)
robust <- args$robust %||% FALSE

model <- lm(formula, data = data)

if (robust) {
  robust_se <- lmtest::coeftest(model, vcov = sandwich::vcovHC(model, type = "HC1"))
  coefficients <- coef(model)
  std_errors <- robust_se[, "Std. Error"]
  t_values <- robust_se[, "t value"]
  p_values <- robust_se[, "Pr(>|t|)"]
} else {
  model_summary <- summary(model)
  coefficients <- coef(model)
  std_errors <- model_summary$coefficients[, "Std. Error"]
  t_values <- model_summary$coefficients[, "t value"]
  p_values <- model_summary$coefficients[, "Pr(>|t|)"]
}

result <- list(
  coefficients = as.list(coefficients),
  std_errors = as.list(std_errors),
  t_values = as.list(t_values),
  p_values = as.list(p_values),
  r_squared = summary(model)$r.squared,
  adj_r_squared = summary(model)$adj.r.squared,
  sigma = summary(model)$sigma,
  df = unname(summary(model)$df),
  model_call = format(model$call),
  robust = robust
)
"""

PANEL_MODEL_SCRIPT = """
# Perform panel data analysis.
data <- as.data.frame(args$data)
formula <- as.formula(args$formula)
index <- args$index
effect <- args$effect %||% "individual"
model_type <- args$model %||% "within"

panel_data <- plm::pdata.frame(data, index = index)
panel_model <- plm::plm(formula, data = panel_data, effect = effect, model = model_type)
model_summary <- summary(panel_model)
coeffs <- coef(panel_model)
std_err <- model_summary$coefficients[, "Std. Error"]

if ("t value" %in% colnames(model_summary$coefficients)) {
  t_vals <- model_summary$coefficients[, "t value"]
} else {
  t_vals <- rep(NA, length(coeffs))
}

p_vals <- model_summary$coefficients[, "Pr(>|t|)"]

result <- list(
  coefficients = as.list(coeffs),
  std_errors = as.list(std_err),
  t_values = as.list(t_vals),
  p_values = as.list(p_vals),
  r_squared = model_summary$r.squared,
  adj_r_squared = model_summary$adj.r.squared,
  model_call = format(panel_model$call),
  model_type = model_type,
  effect_type = effect
)
"""

IV_REGRESSION_SCRIPT = """
# Perform instrumental variables regression.
data <- as.data.frame(args$data)
formula <- as.formula(args$formula)

iv_model <- AER::ivreg(formula, data = data)
model_summary <- summary(iv_model)
result <- list(
  coefficients = as.list(coef(iv_model)),
  std_errors = as.list(model_summary$coefficients[, "Std. Error"]),
  t_values = as.list(model_summary$coefficients[, "t value"]),
  p_values = as.list(model_summary$coefficients[, "Pr(>|t|)"]),
  r_squared = model_summary$r.squared,
  adj_r_squared = model_summary$adj.r.squared,
  sigma = model_summary$sigma,
  model_call = format(iv_model$call)
)
"""

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
def linear_model(formula: str, data: Dict[str, Any], robust: bool = False) -> Dict[str, Any]:
    args = {"formula": formula, "data": data, "robust": robust}
    return execute_r_script(LINEAR_REGRESSION_SCRIPT, args)

@mcp.tool(
    name="panel_model",
    description="Run a panel data model",
    input_schema={
        "type": "object",
        "properties": {
            "formula": {"type": "string", "description": "The regression formula (e.g., 'y ~ x1 + x2')"},
            "data": {"type": "object", "description": "Dataset as a dictionary/JSON object"},
            "index": {"type": "array", "description": "Panel index variables (e.g., ['individual', 'time'])"},
            "effect": {"type": "string", "description": "Type of effects: 'individual', 'time', or 'twoways'"},
            "model": {"type": "string", "description": "Model type: 'within', 'random', 'pooling', 'between', or 'fd'"}
        },
        "required": ["formula", "data", "index"]
    }
)
def panel_model(formula: str, data: Dict[str, Any], index: List[str], effect: str = "individual", model: str = "within") -> Dict[str, Any]:
    args = {"formula": formula, "data": data, "index": index, "effect": effect, "model": model}
    return execute_r_script(PANEL_MODEL_SCRIPT, args)

@mcp.tool(
    name="iv_regression",
    description="Estimate instrumental variables regression",
    input_schema={
        "type": "object",
        "properties": {
            "formula": {"type": "string", "description": "The regression formula (e.g., 'y ~ x1 + x2 | z1 + z2')"},
            "data": {"type": "object", "description": "Dataset as a dictionary/JSON object"}
        },
        "required": ["formula", "data"]
    }
)
def iv_regression(formula: str, data: Dict[str, Any]) -> Dict[str, Any]:
    args = {"formula": formula, "data": data}
    return execute_r_script(IV_REGRESSION_SCRIPT, args)
