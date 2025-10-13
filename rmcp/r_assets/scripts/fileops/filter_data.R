# Data Filtering Script for RMCP
# ==============================
#
# This script filters datasets based on multiple conditions with logical operators.
# Supports various comparison operators and flexible condition combinations.


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
library(dplyr)

# Prepare data and parameters
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
# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
