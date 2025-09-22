# Data Filtering Script for RMCP
# ==============================
#
# This script filters datasets based on multiple conditions with logical operators.
# Supports various comparison operators and flexible condition combinations.

library(dplyr)

# Prepare data and parameters
data <- as.data.frame(args$data)
conditions <- args$conditions
logic <- args$logic %||% "AND"

# Build filter expressions
filter_expressions <- c()

for (condition in conditions) {
    var <- condition$variable
    op <- condition$operator
    val <- condition$value
    
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

# Combine expressions
if (logic == "AND") {
    full_expression <- paste(filter_expressions, collapse = " & ")
} else {
    full_expression <- paste(filter_expressions, collapse = " | ")
}

# Apply filter
filtered_data <- data %>% filter(eval(parse(text = full_expression)))

result <- list(
    data = filtered_data,
    filter_expression = full_expression,
    original_rows = nrow(data),
    filtered_rows = nrow(filtered_data),
    rows_removed = nrow(data) - nrow(filtered_data),
    removal_percentage = (nrow(data) - nrow(filtered_data)) / nrow(data) * 100
)