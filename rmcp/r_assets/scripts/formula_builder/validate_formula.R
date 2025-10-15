# Formula Validation Script for RMCP
# ===================================
#
# This script validates R formulas against provided data to ensure
# variable existence and identify potential data quality issues.

# Convert data to data frame if needed
if (!is.data.frame(data)) {
  data <- as.data.frame(data)
}

formula_str <- args$formula

# Parse formula
tryCatch(
  {
    parsed_formula <- as.formula(formula_str)
    # Extract variable names
    vars_in_formula <- all.vars(parsed_formula)
    vars_in_data <- names(data)

    # Check which variables exist
    missing_vars <- vars_in_formula[!vars_in_formula %in% vars_in_data]
    existing_vars <- vars_in_formula[vars_in_formula %in% vars_in_data]

    # Get variable types for existing variables
    var_types <- sapply(data[existing_vars], class)

    # Check for potential issues
    warnings <- c()

    # Check for missing values
    missing_counts <- sapply(data[existing_vars], function(x) sum(is.na(x)))
    high_missing <- names(missing_counts[missing_counts > 0.1 * nrow(data)])
    if (length(high_missing) > 0) {
      warnings <- c(warnings, paste("High missing values in:", paste(high_missing, collapse = ", ")))
    }
    # Check for character variables (might need factors)
    char_vars <- names(var_types[var_types == "character"])
    if (length(char_vars) > 0) {
      warnings <- c(warnings, paste("Character variables (consider converting to factors):", paste(char_vars, collapse = ", ")))
    }
    result <- list(
      is_valid = length(missing_vars) == 0,
      missing_variables = missing_vars,
      existing_variables = existing_vars,
      available_variables = vars_in_data,
      variable_types = as.list(setNames(var_types, names(var_types))),
      warnings = if (length(warnings) == 0) character(0) else warnings,
      formula_parsed = TRUE
    )
  },
  error = function(e) {
    result <- list(
      is_valid = FALSE,
      error = e$message,
      formula_parsed = FALSE
    )
  }
)
