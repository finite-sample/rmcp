# Lag and Lead Variables Creation Script for RMCP
# ================================================
#
# This script creates lagged and lead variables for time series analysis,
# useful for autoregressive modeling and causal inference.

# Load required libraries
library(knitr)

# Prepare data and parameters
variables <- args$variables
lags <- args$lags %||% c(1)
leads <- args$leads %||% c()

# Load required libraries
result_data <- data

# Create lagged variables
for (var in variables) {
  for (lag_val in lags) {
    new_var <- paste0(var, "_lag", lag_val)
    result_data[[new_var]] <- c(rep(NA, lag_val), head(data[[var]], -lag_val))
  }
}

# Create lead variables
for (var in variables) {
  for (lead_val in leads) {
    new_var <- paste0(var, "_lead", lead_val)
    result_data[[new_var]] <- c(tail(data[[var]], -lead_val), rep(NA, lead_val))
  }
}
# Get created variables and ensure it's always an array
created_vars <- names(result_data)[!names(result_data) %in% names(data)]
if (length(created_vars) == 0) {
  created_vars <- character(0)
}
result <- list(
  data = as.list(result_data),
  variables_created = I(as.character(created_vars)),
  n_obs = nrow(result_data),
  operation = "lag_lead",
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Create lag/lead summary table
        lagLead_summary <- data.frame(
          Operation = "Lag/Lead",
          Variables_Input = length(variables),
          Variables_Created = length(created_vars),
          Observations = nrow(result_data)
        )
        paste(as.character(knitr::kable(
          lagLead_summary,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        "Lag/lead variables created successfully"
      }
    ),
    interpretation = paste0(
      "Created ", length(created_vars), " lag/lead variables from ",
      length(variables), " input variables."
    )
  )
)
