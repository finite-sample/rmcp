# Dataset Information Analysis Script for RMCP
# ============================================
#
# This script provides comprehensive information about a dataset including
# dimensions, variable types, missing values, and memory usage.

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
include_sample <- args$include_sample %||% TRUE
sample_size <- args$sample_size %||% 5

# Basic info
n_rows <- nrow(data)
n_cols <- ncol(data)
col_names <- names(data)

# Variable types - ensure all are arrays
var_types <- sapply(data, class)
numeric_vars <- names(data)[sapply(data, is.numeric)]
character_vars <- names(data)[sapply(data, is.character)]
factor_vars <- names(data)[sapply(data, is.factor)]
logical_vars <- names(data)[sapply(data, is.logical)]
date_vars <- names(data)[sapply(data, function(x) inherits(x, "Date"))]

# Ensure variables are always arrays even if empty or single
numeric_vars <- if (length(numeric_vars) == 0) character(0) else numeric_vars
character_vars <- if (length(character_vars) == 0) character(0) else character_vars
factor_vars <- if (length(factor_vars) == 0) character(0) else factor_vars
logical_vars <- if (length(logical_vars) == 0) character(0) else logical_vars
date_vars <- if (length(date_vars) == 0) character(0) else date_vars

# Missing value analysis
missing_counts <- sapply(data, function(x) sum(is.na(x)))
missing_percentages <- missing_counts / n_rows * 100

# Memory usage
memory_usage <- object.size(data)

result <- list(
  dimensions = list(rows = n_rows, columns = n_cols),
  variables = list(
    all = I(col_names),
    numeric = I(numeric_vars),
    character = I(character_vars),
    factor = I(factor_vars),
    logical = I(logical_vars),
    date = I(date_vars)
  ),
  variable_types = as.list(var_types),
  missing_values = list(
    counts = as.list(missing_counts),
    percentages = as.list(missing_percentages),
    total_missing = sum(missing_counts),
    complete_cases = sum(complete.cases(data))
  ),
  memory_usage_bytes = as.numeric(memory_usage)
)

# Add data sample if requested
if (include_sample && n_rows > 0) {
  sample_rows <- min(sample_size, n_rows)
  result$sample_data <- as.list(head(data, sample_rows))
}
# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
