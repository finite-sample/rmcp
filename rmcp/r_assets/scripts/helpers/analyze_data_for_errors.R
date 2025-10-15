# Data Error Analysis Script for RMCP
# ====================================
#
# This script analyzes data to identify potential issues that might
# cause errors during statistical analysis.

# Prepare data
n_rows <- nrow(data)
n_cols <- ncol(data)

# Load required libraries

# Basic data analysis
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
