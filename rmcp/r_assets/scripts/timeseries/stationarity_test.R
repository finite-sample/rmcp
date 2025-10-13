# Stationarity Testing Script for RMCP
# =====================================
#
# This script performs stationarity tests on time series data using
# Augmented Dickey-Fuller, KPSS, or Phillips-Perron tests.


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
library(tseries)

# Prepare data and parameters
test_type <- args$test %||% "adf"
ts_data <- ts(values)

if (test_type == "adf") {
  test_result <- adf.test(ts_data)
  test_name <- "Augmented Dickey-Fuller"
} else if (test_type == "kpss") {
  test_result <- kpss.test(ts_data)
  test_name <- "KPSS"
} else if (test_type == "pp") {
  test_result <- pp.test(ts_data)
  test_name <- "Phillips-Perron"
}

# Handle critical values properly - some tests might not have them
critical_vals <- if (is.null(test_result$critical) || length(test_result$critical) == 0) {
  # Return empty named list to ensure it's treated as object, not array
  structure(list(), names = character(0))
} else {
  as.list(test_result$critical)
}

result <- list(
  test_name = test_name,
  test_type = test_type,
  statistic = as.numeric(test_result$statistic),
  p_value = test_result$p.value,
  critical_values = critical_vals,
  alternative = test_result$alternative,
  is_stationary = if (test_type == "kpss") test_result$p.value > 0.05 else test_result$p.value < 0.05,
  n_obs = length(values),

  # Special non-validated field for formatting
  "_formatting" = list(
    summary = format_result_table(test_result, paste0(test_name, " Test Results")),
    interpretation = paste0(
      test_name, " test: ",
      get_significance(test_result$p.value),
      if (test_type == "kpss") {
        if (test_result$p.value > 0.05) " - series appears stationary" else " - series appears non-stationary"
      } else {
        if (test_result$p.value < 0.05) " - series appears stationary" else " - series appears non-stationary"
      }
    )
  )
)
# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
