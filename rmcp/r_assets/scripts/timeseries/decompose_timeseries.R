# Time Series Decomposition Script for RMCP
# ==========================================
#
# This script decomposes time series into trend, seasonal, and remainder
# components using additive or multiplicative decomposition methods.

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
frequency <- args$frequency %||% 12
decomp_type <- args$type %||% "additive"

# Create time series
ts_data <- ts(values, frequency = frequency)

# Decompose
if (decomp_type == "multiplicative") {
  decomp <- decompose(ts_data, type = "multiplicative")
} else {
  decomp <- decompose(ts_data, type = "additive")
}

# Handle NA values properly for JSON - use I() to preserve arrays
result <- list(
  original = I(as.numeric(decomp$x)),
  trend = I(as.numeric(decomp$trend)),
  seasonal = I(as.numeric(decomp$seasonal)),
  remainder = I(as.numeric(decomp$random)),
  type = decomp_type,
  frequency = frequency,
  n_obs = length(values),

  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Create decomposition summary table
        decomp_summary <- data.frame(
          Component = c("Original", "Trend", "Seasonal", "Remainder"),
          Missing_Values = c(
            sum(is.na(decomp$x)),
            sum(is.na(decomp$trend)),
            sum(is.na(decomp$seasonal)),
            sum(is.na(decomp$random))
          ),
          Type = c(decomp_type, decomp_type, decomp_type, decomp_type)
        )
        as.character(knitr::kable(
          decomp_summary,
          format = "markdown", digits = 4
        ))
      },
      error = function(e) {
        "Time series decomposition completed successfully"
      }
    ),
    interpretation = paste0("Time series decomposed using ", decomp_type, " method with frequency ", frequency, ".")
  )
)
# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
