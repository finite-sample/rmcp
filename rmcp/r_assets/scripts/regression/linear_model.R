# Linear Regression Analysis Script for RMCP
# ===========================================
#
# This script performs comprehensive linear regression analysis using R's lm() function.
# It supports weighted regression, missing value handling, and returns detailed
# model diagnostics including coefficients, significance tests, and goodness-of-fit.

# Prepare data and parameters

# Load required libraries
library(jsonlite)

# Determine script directory for path resolution
script_dir <- if (exists("testthat_testing") && testthat_testing) {
  # Running under testthat - use relative path from test directory
  file.path("..", "..", "R")
} else {
  # Running normally - use relative path from script location
  file.path("..", "..", "R")
}

# Load RMCP utilities
utils_path <- file.path(script_dir, "utils.R")
if (file.exists(utils_path)) {
  source(utils_path)
} else {
  stop("Cannot find RMCP utilities at: ", utils_path)
}

# Parse command line arguments
args <- if (exists("test_args")) {
  # Use test arguments if provided (for testthat)
  test_args
} else {
  # Parse from command line
  cmd_args <- commandArgs(trailingOnly = TRUE)
  if (length(cmd_args) == 0) {
    stop("No JSON arguments provided")
  }

  # Parse JSON input
  tryCatch(
    {
      fromJSON(cmd_args[1])
    },
    error = function(e) {
      stop("Failed to parse JSON arguments: ", e$message)
    }
  )
}


# Validate input
args <- validate_json_input(args, required = c("data"))

# Main script logic
formula <- as.formula(args$formula)

# Handle optional parameters
weights <- args$weights
na_action <- args$na_action %||% "na.omit"

# Fit model
if (!is.null(weights)) {
  model <- lm(formula, data = data, weights = weights, na.action = get(na_action))
} else {
  model <- lm(formula, data = data, na.action = get(na_action))
}

# Get comprehensive results
summary_model <- summary(model)

# Generate formatted summary using our formatting functions
formatted_summary <- format_lm_results(model, args$formula)

# Generate natural language interpretation
interpretation <- interpret_lm(model)

result <- list(
  # Schema-compliant fields only (strict validation)
  coefficients = as.list(coef(model)),
  std_errors = as.list(summary_model$coefficients[, "Std. Error"]),
  t_values = as.list(summary_model$coefficients[, "t value"]),
  p_values = as.list(summary_model$coefficients[, "Pr(>|t|)"]),
  r_squared = summary_model$r.squared,
  adj_r_squared = summary_model$adj.r.squared,
  f_statistic = summary_model$fstatistic[1],
  f_p_value = pf(summary_model$fstatistic[1],
    summary_model$fstatistic[2],
    summary_model$fstatistic[3],
    lower.tail = FALSE
  ),
  residual_se = summary_model$sigma,
  df_residual = summary_model$df[2],
  fitted_values = as.numeric(fitted(model)),
  residuals = as.numeric(residuals(model)),
  n_obs = nrow(model$model),
  method = "lm",

  # Special non-validated field for formatting (will be extracted before validation)
  "_formatting" = list(
    summary = formatted_summary,
    interpretation = interpretation
  )
)
# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
