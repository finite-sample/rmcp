# RMCP R Script Template
# =====================
# Standard boilerplate for all RMCP R scripts
# This ensures consistent argument parsing, error handling, and output formatting

# Load required libraries
library(jsonlite)

# Determine script directory for path resolution
script_dir <- if (exists("testthat_testing") && testthat_testing) {
  # Running under testthat - use relative path from test directory
  file.path("..", "..", "R")
} else {
  # Running normally - use relative path from script location
  script_path <- if (interactive()) {
    # In interactive session, use working directory
    "."
  } else {
    # In script execution, get script's directory
    normalizePath(dirname(sys.frame(1)$ofile))
  }
  file.path(script_path, "..", "..", "R")
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

# Script-specific validation will be added here
# validate_json_input(args, required = c("data"))

# Main script logic will be implemented here
# result <- list(...)

# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
