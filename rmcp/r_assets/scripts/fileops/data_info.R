# Dataset Information Analysis Script for RMCP
# ============================================
#
# This script provides comprehensive information about a dataset including
# dimensions, variable types, missing values, and memory usage.

# Prepare data and parameters
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
