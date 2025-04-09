import os
import json
import tempfile
import subprocess
from typing import Dict, List, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

# Initialize the MCP server using FastMCP from our package.
mcp = FastMCP(
    name="R Econometrics",
    version="0.1.0",
    description="A Model Context Protocol server for R-based econometric analysis"
)

def execute_r_script(script: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an R script with the given arguments and return the results.
    
    This version captures and prints stdout and stderr from the Rscript call.
    
    Args:
        script: The R script to execute.
        args: Arguments to pass to the R script.
        
    Returns:
        The results of the R execution as a dictionary.
    """
    with tempfile.NamedTemporaryFile(suffix='.R', delete=False, mode='w') as script_file, \
         tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as args_file, \
         tempfile.NamedTemporaryFile(suffix='.json', delete=False) as result_file:
        
        script_path = script_file.name
        args_path = args_file.name
        result_path = result_file.name
        
        # Write the script and arguments to temporary files.
        script_file.write(script)
        json.dump(args, args_file)
    
    try:
        # Construct the R command.
        r_command = f"""
        library(jsonlite)
        library(plm)
        library(lmtest)
        library(sandwich)
        library(AER)
        
        # Define NULL coalescing operator if not available.
        '%||%' <- function(x, y) if (is.null(x)) y else x
        
        # Read arguments from the temporary file.
        args <- fromJSON('{args_path}')
        
        # Execute the provided R script.
        {script}
        
        # Write the results to the temporary results file.
        writeLines(toJSON(result, auto_unbox = TRUE), '{result_path}')
        """
        
        try:
            subprocess.run(
                ['Rscript', '-e', r_command],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            print("Rscript STDOUT:")
            print(e.stdout)
            print("Rscript STDERR:")
            print(e.stderr)
            raise
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        return result
    
    finally:
        for file_path in [script_path, args_path, result_path]:
            try:
                os.unlink(file_path)
            except Exception:
                pass

# Define the R script for a linear regression model.
LINEAR_REGRESSION_SCRIPT = """
# Perform linear regression.
data <- as.data.frame(args$data)
formula <- as.formula(args$formula)
robust <- args$robust %||% FALSE

# Fit the model.
model <- lm(formula, data = data)

# Format the results.
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

# Define the R script for panel data analysis.
PANEL_MODEL_SCRIPT = """
# Perform panel data analysis.
data <- as.data.frame(args$data)
formula <- as.formula(args$formula)
index <- args$index
effect <- args$effect %||% "individual"
model_type <- args$model %||% "within"

# Create the panel data object.
panel_data <- plm::pdata.frame(data, index = index)

# Fit the panel data model.
panel_model <- plm::plm(
  formula,
  data = panel_data,
  effect = effect,
  model = model_type
)

# Extract the results.
model_summary <- summary(panel_model)
result <- list(
  coefficients = as.list(coef(panel_model)),
  std_errors = as.list(model_summary$coefficients[, "Std. Error"]),
  t_values = as.list(model_summary$coefficients[, "t value"]),
  p_values = as.list(model_summary$coefficients[, "Pr(>|t|)"]),
  r_squared = model_summary$r.squared,
  adj_r_squared = model_summary$adj.r.squared,
  model_call = format(panel_model$call),
  model_type = model_type,
  effect_type = effect
)
"""

# Define the R script for diagnostic tests.
DIAGNOSTICS_SCRIPT = """
# Perform model diagnostics.
data <- as.data.frame(args$data)
formula <- as.formula(args$formula)
tests <- args$tests

# Fit a linear model.
model <- lm(formula, data = data)

# Initialize an empty list for test results.
results <- list()

# Run the requested diagnostic tests.
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

# Define the R script for instrumental variables regression.
IV_REGRESSION_SCRIPT = """
# Perform instrumental variables regression.
data <- as.data.frame(args$data)
formula <- as.formula(args$formula)

# Fit the IV regression model.
iv_model <- AER::ivreg(formula, data = data)

# Extract the model results.
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

# Register the linear_model tool.
@mcp.tool(
    name="linear_model",
    description="Run a linear regression model",
    input_schema={
        "type": "object",
        "properties": {
            "formula": {
                "type": "string",
                "description": "The regression formula (e.g., 'y ~ x1 + x2')"
            },
            "data": {
                "type": "object",
                "description": "Dataset as a dictionary/JSON object"
            },
            "robust": {
                "type": "boolean",
                "description": "Whether to use robust standard errors"
            }
        },
        "required": ["formula", "data"]
    }
)
def linear_model(formula: str, data: Dict[str, Any], robust: bool = False) -> Dict[str, Any]:
    args = {
        "formula": formula,
        "data": data,
        "robust": robust
    }
    return execute_r_script(LINEAR_REGRESSION_SCRIPT, args)

# Register the panel_model tool.
@mcp.tool(
    name="panel_model",
    description="Run a panel data model",
    input_schema={
        "type": "object",
        "properties": {
            "formula": {
                "type": "string",
                "description": "The regression formula (e.g., 'y ~ x1 + x2')"
            },
            "data": {
                "type": "object",
                "description": "Dataset as a dictionary/JSON object"
            },
            "index": {
                "type": "array",
                "description": "Panel index variables (e.g., ['individual', 'time'])"
            },
            "effect": {
                "type": "string",
                "description": "Type of effects: 'individual', 'time', or 'twoways'"
            },
            "model": {
                "type": "string",
                "description": "Model type: 'within', 'random', 'pooling', 'between', or 'fd'"
            }
        },
        "required": ["formula", "data", "index"]
    }
)
def panel_model(formula: str, data: Dict[str, Any], index: List[str], effect: str = "individual", model: str = "within") -> Dict[str, Any]:
    args = {
        "formula": formula,
        "data": data,
        "index": index,
        "effect": effect,
        "model": model
    }
    return execute_r_script(PANEL_MODEL_SCRIPT, args)

# Register the diagnostics tool.
@mcp.tool(
    name="diagnostics",
    description="Perform model diagnostics",
    input_schema={
        "type": "object",
        "properties": {
            "formula": {
                "type": "string",
                "description": "The regression formula (e.g., 'y ~ x1 + x2')"
            },
            "data": {
                "type": "object",
                "description": "Dataset as a dictionary/JSON object"
            },
            "tests": {
                "type": "array",
                "description": "Tests to run (e.g., ['bp', 'reset', 'dw'])"
            }
        },
        "required": ["formula", "data", "tests"]
    }
)
def diagnostics(formula: str, data: Dict[str, Any], tests: List[str]) -> Dict[str, Any]:
    args = {
        "formula": formula,
        "data": data,
        "tests": tests
    }
    return execute_r_script(DIAGNOSTICS_SCRIPT, args)

# Register the iv_regression tool.
@mcp.tool(
    name="iv_regression",
    description="Estimate instrumental variables regression",
    input_schema={
        "type": "object",
        "properties": {
            "formula": {
                "type": "string",
                "description": "The regression formula (e.g., 'y ~ x1 + x2 | z1 + z2')"
            },
            "data": {
                "type": "object",
                "description": "Dataset as a dictionary/JSON object"
            }
        },
        "required": ["formula", "data"]
    }
)
def iv_regression(formula: str, data: Dict[str, Any]) -> Dict[str, Any]:
    args = {
        "formula": formula,
        "data": data
    }
    return execute_r_script(IV_REGRESSION_SCRIPT, args)

# Register resource endpoints.
@mcp.resource("econometrics:formulas")
def get_econometrics_formulas() -> str:
    return """
Common Econometric Formula Patterns:

1. Simple Linear Regression: y ~ x
2. Multiple Linear Regression: y ~ x1 + x2 + x3
3. Interaction Terms: y ~ x1 + x2 + x1:x2
4. Polynomial Terms: y ~ x + I(x^2) + I(x^3)
5. Log-Linear Model: log(y) ~ x1 + x2 + x3
6. Log-Log Model: log(y) ~ log(x1) + log(x2)
7. Fixed Effects Panel: y ~ x1 + x2 + factor(id)
8. Instrumental Variables: y ~ x1 + x2 | z1 + z2 + x2
   Where variables after | are instruments
    """

@mcp.resource("econometrics:diagnostics")
def get_econometrics_diagnostics() -> str:
    return """
Common Econometric Diagnostics:

1. Breusch-Pagan Test (bp): Tests for heteroskedasticity
   - H0: Homoskedasticity (constant variance)
   - H1: Heteroskedasticity (non-constant variance)

2. Ramsey RESET Test (reset): Tests for functional form misspecification
   - H0: Model is correctly specified
   - H1: Model has omitted nonlinearities

3. Durbin-Watson Test (dw): Tests for autocorrelation
   - H0: No autocorrelation
   - H1: Positive/negative autocorrelation

4. Hausman Test: Tests for consistency of random effects estimator
   - H0: Random effects model is consistent
   - H1: Fixed effects model is preferred

5. Unit Root Tests: Tests for stationarity in time series
   - H0: Series has a unit root (non-stationary)
   - H1: Series is stationary
    """

@mcp.resource("econometrics:panel_data")
def get_panel_data_info() -> str:
    return """
Panel Data Analysis in R:

Panel data (also known as longitudinal data) has observations on multiple entities observed at multiple points in time.

Key panel data models in R using the 'plm' package:

1. Pooled OLS Model (model = "pooling"):
   - Ignores panel structure.
   - Assumes homogeneity across entities and time.

2. Fixed Effects Model (model = "within"):
   - Controls for time-invariant unobserved heterogeneity.
   - Uses variation within entities over time.

3. Random Effects Model (model = "random"):
   - Assumes unobserved heterogeneity is uncorrelated with regressors.
   - More efficient than fixed effects if the assumption holds.

4. First-Difference Model (model = "fd"):
   - Eliminates time-invariant effects by differencing.
   - Useful for addressing certain forms of endogeneity.

5. Between Model (model = "between"):
   - Uses entity means (cross-sectional variation).
   - Ignores within-entity variation.

Effects specifications:
- individual: Entity fixed/random effects.
- time: Time fixed/random effects.
- twoways: Both entity and time effects.
    """

# Register prompt endpoints.
@mcp.prompt("panel_data_analysis")
def panel_data_analysis_prompt(dataset_name: str, dependent_var: str, independent_vars: str) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": {
                "type": "text",
                "text": "You are an econometrics assistant helping a researcher with panel data analysis."
            }
        },
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""
I'm analyzing panel data in the dataset '{dataset_name}'. 
I want to examine the relationship between my dependent variable {dependent_var} and independent variables {independent_vars}.

Please help me:
1. Run both fixed effects and random effects models
2. Determine which model is more appropriate using the Hausman test
3. Interpret the coefficients
4. Check for heteroskedasticity and autocorrelation
5. Suggest any necessary corrections to the model
                """
            }
        }
    ]

@mcp.prompt("time_series_analysis")
def time_series_analysis_prompt(dataset_name: str, time_var: str, dependent_var: str) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": {
                "type": "text",
                "text": "You are an econometrics assistant helping a researcher with time series analysis."
            }
        },
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""
I'm analyzing time series data in the dataset '{dataset_name}' with time variable {time_var} and I'm interested in the variable {dependent_var}.

Please help me:
1. Check for stationarity using unit root tests
2. Transform the data if necessary (differencing, logging)
3. Identify the appropriate ARIMA model
4. Estimate the model and interpret results
5. Perform diagnostic checks
6. Create forecasts if appropriate
                """
            }
        }
    ]

def main():
    """
    Run the MCP server via standard I/O.
    """
    return stdio_server(mcp)


if __name__ == "__main__":
    main()