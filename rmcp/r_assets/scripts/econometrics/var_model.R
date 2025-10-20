# Vector Autoregression (VAR) Model Script for RMCP
# ===================================================
#
# This script fits Vector Autoregression models for multivariate time series
# analysis with support for different lag orders and deterministic terms.

# Load required libraries
library(vars)
library(knitr)

# Prepare data and parameters
variables <- args$variables
lag_order <- args$lags %||% 2
var_type <- args$type %||% "const"

# Select variables for VAR
var_data <- data[, variables, drop = FALSE]

# Remove missing values
var_data <- na.omit(var_data)

# Fit VAR model
var_model <- VAR(var_data, p = lag_order, type = var_type)

# Extract coefficients for each equation
equations <- list()
for (var in variables) {
  eq_summary <- summary(var_model)$varresult[[var]]
  equations[[var]] <- list(
    coefficients = as.list(coef(eq_summary)),
    std_errors = as.list(eq_summary$coefficients[, "Std. Error"]),
    t_values = as.list(eq_summary$coefficients[, "t value"]),
    p_values = as.list(eq_summary$coefficients[, "Pr(>|t|)"]),
    r_squared = eq_summary$r.squared,
    adj_r_squared = eq_summary$adj.r.squared
  )
}
# Model diagnostics
var_summary <- summary(var_model)
result <- list(
  equations = equations,
  variables = variables,
  lag_order = lag_order,
  var_type = var_type,
  n_obs = var_model$obs,
  n_variables = length(variables),
  loglik = logLik(var_model)[1],
  aic = AIC(var_model),
  bic = BIC(var_model),
  residual_covariance = as.matrix(var_summary$covres),
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Create VAR summary table
        var_summary_df <- data.frame(
          Model = "VAR",
          Variables = length(variables),
          Lags = lag_order,
          Observations = var_model$obs,
          AIC = round(AIC(var_model), 2),
          BIC = round(BIC(var_model), 2)
        )
        paste(as.character(knitr::kable(
          var_summary_df,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        "VAR model fitted successfully"
      }
    ),
    interpretation = paste0(
      "VAR(", lag_order, ") model with ", length(variables),
      " variables and ", var_model$obs, " observations."
    )
  )
)
