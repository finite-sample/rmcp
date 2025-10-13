# Lag and Lead Variables Creation Script for RMCP
# ================================================
#
# This script creates lagged and lead variables for time series analysis,
# useful for autoregressive modeling and causal inference.

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
variables <- args$variables
lags <- args$lags %||% c(1)
leads <- args$leads %||% c()

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
        as.character(knitr::kable(
          lagLead_summary,
          format = "markdown", digits = 4
        ))
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
# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
