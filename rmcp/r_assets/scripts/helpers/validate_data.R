# Data Validation Script for RMCP
# ================================
#
# This script validates data quality and identifies potential issues
# before statistical analysis, with analysis-specific checks.

# Load required libraries
# Prepare data and parameters
analysis_type <- args$analysis_type %||% "general"
strict_mode <- args$strict %||% FALSE

# Basic validation
n_rows <- nrow(data)
n_cols <- ncol(data)
col_names <- names(data)

# Initialize results
validation_results <- list(
  is_valid = TRUE,
  warnings = c(),
  errors = c(),
  suggestions = c(),
  data_quality = list()
)

# Check basic requirements
if (n_rows == 0) {
  validation_results$is_valid <- FALSE
  validation_results$errors <- c(
    validation_results$errors,
    "Dataset is empty (no rows)"
  )
}
if (n_cols == 0) {
  validation_results$is_valid <- FALSE
  validation_results$errors <- c(
    validation_results$errors,
    "Dataset has no columns"
  )
}
# Missing value analysis
missing_counts <- sapply(data, function(x) sum(is.na(x)))
missing_percentages <- missing_counts / n_rows * 100
high_missing <- names(missing_percentages[missing_percentages > 50])
if (length(high_missing) > 0) {
  validation_results$warnings <- c(
    validation_results$warnings,
    paste(
      "High missing values (>50%) in:",
      paste(high_missing, collapse = ", ")
    )
  )
}
# Variable type analysis
var_types <- sapply(data, class)
numeric_vars <- names(var_types[var_types %in% c("numeric", "integer")])
character_vars <- names(var_types[var_types == "character"])
factor_vars <- names(var_types[var_types == "factor"])
logical_vars <- names(var_types[var_types == "logical"])
# Analysis-specific validation
if (analysis_type == "regression") {
  if (n_cols < 2) {
    validation_results$errors <- c(
      validation_results$errors,
      "Regression requires at least 2 variables (outcome + predictor)"
    )
  }
  if (n_rows < 10) {
    validation_results$warnings <- c(
      validation_results$warnings,
      "Small sample size for regression (n < 10)"
    )
  }
  if (length(numeric_vars) == 0) {
    validation_results$warnings <- c(
      validation_results$warnings,
      "No numeric variables found - may need conversion"
    )
  }
}
if (analysis_type == "correlation") {
  if (length(numeric_vars) < 2) {
    validation_results$errors <- c(validation_results$errors, "Correlation requires at least 2 numeric variables")
  }
  if (n_rows < 3) {
    validation_results$errors <- c(validation_results$errors, "Correlation requires at least 3 observations")
  }
}
if (analysis_type == "timeseries") {
  if (n_rows < 10) {
    validation_results$warnings <- c(validation_results$warnings, "Small sample size for time series (n < 10)")
  }
  if (length(numeric_vars) == 0) {
    validation_results$errors <- c(validation_results$errors, "Time series analysis requires numeric variables")
  }
}
if (analysis_type == "classification") {
  # Look for binary/categorical variables
  binary_vars <- names(data)[sapply(data, function(x) length(unique(x[!is.na(x)])) == 2)]
  if (length(binary_vars) == 0 && length(factor_vars) == 0) {
    validation_results$warnings <- c(validation_results$warnings, "No obvious outcome variable for classification found")
  }
}
# Data quality checks
# Constant variables
constant_vars <- names(data)[sapply(data, function(x) length(unique(x[!is.na(x)])) <= 1)]
if (length(constant_vars) > 0) {
  validation_results$warnings <- c(
    validation_results$warnings,
    paste("Constant variables (no variation):", paste(constant_vars, collapse = ", "))
  )
}
# Outliers (for numeric variables)
outlier_info <- list()
for (var in numeric_vars) {
  if (sum(!is.na(data[[var]])) > 0) {
    Q1 <- quantile(data[[var]], 0.25, na.rm = TRUE)
    Q3 <- quantile(data[[var]], 0.75, na.rm = TRUE)
    IQR <- Q3 - Q1
    outliers <- sum(data[[var]] < (Q1 - 1.5 * IQR) | data[[var]] > (Q3 + 1.5 * IQR), na.rm = TRUE)
    outlier_percentage <- outliers / sum(!is.na(data[[var]])) * 100
    if (outlier_percentage > 10) {
      outlier_info[[var]] <- outlier_percentage
    }
  }
}
if (length(outlier_info) > 0) {
  validation_results$warnings <- c(
    validation_results$warnings,
    paste("High outlier percentage in:", paste(names(outlier_info), collapse = ", "))
  )
}
# Strict mode additional checks
if (strict_mode) {
  # Check for duplicate rows
  duplicate_rows <- sum(duplicated(data))
  if (duplicate_rows > 0) {
    validation_results$warnings <- c(
      validation_results$warnings,
      paste("Duplicate rows found:", duplicate_rows)
    )
  }
  # Check variable name issues
  problematic_names <- col_names[grepl("[^a-zA-Z0-9_.]", col_names)]
  if (length(problematic_names) > 0) {
    validation_results$warnings <- c(
      validation_results$warnings,
      paste("Variable names with special characters:", paste(problematic_names, collapse = ", "))
    )
  }
  # Check for very wide data
  if (n_cols > n_rows && n_rows < 100) {
    validation_results$warnings <- c(
      validation_results$warnings,
      "More variables than observations - may be problematic"
    )
  }
}
# Generate suggestions
suggestions <- c()
if (length(character_vars) > 0) {
  suggestions <- c(suggestions, paste("Consider converting character variables to factors:", paste(character_vars[1:min(3, length(character_vars))], collapse = ", ")))
}
if (any(missing_percentages > 10)) {
  suggestions <- c(suggestions, "Consider handling missing values before analysis")
}
if (length(constant_vars) > 0) {
  suggestions <- c(suggestions, "Remove constant variables as they don't contribute to analysis")
}
if (n_rows < 30) {
  suggestions <- c(suggestions, "Small sample size - interpret results cautiously")
}
validation_results$suggestions <- suggestions
# Data quality summary
validation_results$data_quality <- list(
  dimensions = list(rows = n_rows, columns = n_cols),
  variable_types = list(
    numeric = length(numeric_vars),
    character = length(character_vars),
    factor = length(factor_vars),
    logical = length(logical_vars)
  ),
  missing_values = list(
    total_missing_cells = sum(missing_counts),
    variables_with_missing = sum(missing_counts > 0),
    max_missing_percentage = if (length(missing_percentages) > 0) max(missing_percentages) else 0
  ),
  data_issues = list(
    constant_variables = length(constant_vars),
    high_outlier_variables = length(outlier_info),
    duplicate_rows = if (strict_mode) duplicate_rows else NA
  )
)
# Ensure arrays are properly formatted for JSON
validation_results$warnings <- if (length(validation_results$warnings) == 0) character(0) else validation_results$warnings
validation_results$errors <- if (length(validation_results$errors) == 0) character(0) else validation_results$errors
validation_results$suggestions <- if (length(validation_results$suggestions) == 0) character(0) else validation_results$suggestions
result <- validation_results
