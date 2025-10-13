# Data Error Analysis Script for RMCP
# ====================================
#
# This script analyzes data to identify potential issues that might
# cause errors during statistical analysis.

# Prepare data

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

# Basic data analysis
n_rows <- nrow(data)
n_cols <- ncol(data)
col_names <- names(data)

# Check for potential issues
issues <- c()
suggestions <- c()

# Missing values
missing_counts <- sapply(data, function(x) sum(is.na(x)))
high_missing <- names(missing_counts[missing_counts > 0.1 * n_rows])
if (length(high_missing) > 0) {
  issues <- c(issues, "High missing values detected")
  suggestions <- c(suggestions, paste(
    "High missing values in:",
    paste(high_missing, collapse = ", ")
  ))
}

# Variable types
var_types <- sapply(data, class)
char_vars <- names(var_types[var_types == "character"])
if (length(char_vars) > 0) {
  suggestions <- c(suggestions, paste(
    "Character variables may need conversion:",
    paste(char_vars, collapse = ", ")
  ))
}

# Small sample size
if (n_rows < 10) {
  issues <- c(issues, "Small sample size")
  suggestions <- c(
    suggestions,
    "Sample size is small - results may be unreliable"
  )
}

# Single column
if (n_cols == 1) {
  issues <- c(issues, "Single variable")
  suggestions <- c(
    suggestions,
    "Only one variable - cannot perform relationship analysis"
  )
}

# Constant variables
constant_vars <- names(data)[sapply(data, function(x) {
  length(unique(x[!is.na(x)])) <= 1
})]
if (length(constant_vars) > 0) {
  issues <- c(issues, "Constant variables detected")
  suggestions <- c(suggestions, paste(
    "Constant variables (no variation):",
    paste(constant_vars, collapse = ", ")
  ))
}

result <- list(
  issues = issues,
  suggestions = suggestions,
  data_summary = list(
    rows = n_rows,
    columns = n_cols,
    missing_values = as.list(missing_counts),
    variable_types = as.list(var_types)
  )
)
# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
