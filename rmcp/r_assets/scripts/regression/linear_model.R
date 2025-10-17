# Linear Regression Analysis Script for RMCP
# ===========================================
#
# This script performs comprehensive linear regression analysis using R's lm() function.
# It supports weighted regression, missing value handling, and returns detailed
# model diagnostics including coefficients, significance tests, and goodness-of-fit.


# Main script logic
formula <- as.formula(args$formula)

# Handle optional parameters
weights <- args$weights
na_action <- args$na_action %||% "na.omit"

# Validate data sufficiency before modeling
n_total <- nrow(data)
if (n_total < 2) {
  stop(
    "Insufficient data: Linear regression requires at least 2 observations. ",
    "Current sample size: ", n_total, ". Please provide more data points."
  )
}

# Fit model
if (!is.null(weights)) {
  model <- lm(formula, data = data, weights = weights, na.action = get(na_action))
} else {
  model <- lm(formula, data = data, na.action = get(na_action))
}

# Check for sufficient degrees of freedom after fitting
n_obs <- nrow(model$model)
n_params <- length(coef(model))
df_residual <- n_obs - n_params

if (df_residual <= 0) {
  stop(
    "Insufficient degrees of freedom: Model has ", n_params, " parameters but only ",
    n_obs, " observations after removing missing values. Need at least ",
    n_params + 1, " observations for reliable estimation."
  )
}

# Get comprehensive results
summary_model <- summary(model)

# Generate formatted summary using our formatting functions
formatted_summary <- format_lm_results(model, args$formula)

# Generate natural language interpretation
interpretation <- interpret_lm(model)

# Calculate F-statistic p-value safely
f_p_value <- tryCatch(
  {
    if (!is.null(summary_model$fstatistic) && length(summary_model$fstatistic) >= 3) {
      pf(
        summary_model$fstatistic[1],
        summary_model$fstatistic[2],
        summary_model$fstatistic[3],
        lower.tail = FALSE
      )
    } else {
      NA_real_
    }
  },
  error = function(e) NA_real_
)

# Ensure all numeric values are valid (not NaN, Inf, or NULL)
clean_numeric <- function(x, default = 0) {
  if (is.null(x) || is.na(x) || is.nan(x) || is.infinite(x)) {
    return(default)
  }
  return(as.numeric(x))
}

result <- list(
  # Schema-compliant fields only (strict validation)
  coefficients = as.list(coef(model)),
  std_errors = as.list(summary_model$coefficients[, "Std. Error"]),
  t_values = as.list(summary_model$coefficients[, "t value"]),
  p_values = as.list(summary_model$coefficients[, "Pr(>|t|)"]),
  r_squared = clean_numeric(summary_model$r.squared, 0),
  adj_r_squared = clean_numeric(summary_model$adj.r.squared, 0),
  f_statistic = clean_numeric(summary_model$fstatistic[1], 0),
  f_p_value = clean_numeric(f_p_value, 1),
  residual_se = clean_numeric(summary_model$sigma, 0),
  df_residual = as.integer(summary_model$df[2]),
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
