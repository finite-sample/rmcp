# Data Filtering Script for RMCP
# ==============================
#
# This script filters datasets based on multiple conditions with logical operators.
# Supports various comparison operators and flexible condition combinations.

# Load required libraries
library(dplyr)

# Prepare data and parameters
conditions <- args$conditions
condition <- args$condition # Support single condition string
logic <- args$logic %||% "AND"

# Build filter expressions
filter_expressions <- c()

# Handle single condition string (backward compatibility)
if (!is.null(condition) && is.character(condition)) {
  filter_expressions <- c(condition)
} else if (!is.null(conditions)) {
  # Handle structured conditions array
  for (cond in conditions) {
    var <- cond$variable
    op <- cond$operator
    val <- cond$value

    if (op == "%in%") {
      expr <- paste0(var, " %in% c(", paste(paste0("'", val, "'"), collapse = ","), ")")
    } else if (op == "!%in%") {
      expr <- paste0("!(", var, " %in% c(", paste(paste0("'", val, "'"), collapse = ","), "))")
    } else if (is.character(val)) {
      expr <- paste0(var, " ", op, " '", val, "'")
    } else {
      expr <- paste0(var, " ", op, " ", val)
    }
    filter_expressions <- c(filter_expressions, expr)
  }
} else {
  stop("Either 'condition' (string) or 'conditions' (array) must be provided")
}
# Combine expressions
if (logic == "AND") {
  full_expression <- paste(filter_expressions, collapse = " & ")
} else {
  full_expression <- paste(filter_expressions, collapse = " | ")
}
# Apply filter with error handling
filtered_data <- tryCatch(
  {
    data %>% filter(eval(parse(text = full_expression)))
  },
  error = function(e) {
    stop(paste("Filter expression failed:", full_expression, "Error:", e$message))
  }
)
result <- list(
  data = filtered_data,
  filter_expression = full_expression,
  original_rows = nrow(data),
  filtered_rows = nrow(filtered_data),
  rows_removed = nrow(data) - nrow(filtered_data),
  removal_percentage = (nrow(data) - nrow(filtered_data)) / nrow(data) * 100
)
