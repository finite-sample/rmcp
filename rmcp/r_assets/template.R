# === RMCP INITIALIZED SCRIPT ===
# This script has been automatically prepared with:
# - All utility functions pre-loaded
# - Arguments parsed and validated
# - Data prepared and available

# Load required libraries
library(jsonlite)

# === RMCP UTILITIES ===
{{ UTILITIES }}

# === AUTOMATIC ARGUMENT PARSING ===
# Arguments are automatically provided by the RMCP loader system
# The 'args' variable contains validated input parameters
# The 'data' variable contains the main dataset (if provided)

# Parse arguments from command line if not already provided
if (!exists("args") || is.function(args)) {
  # Handle command line execution
  cmd_args <- commandArgs(trailingOnly = TRUE)
  if (length(cmd_args) == 0) {
    stop("No JSON arguments provided. This script should be executed through the RMCP system.")
  }
  args <- tryCatch(
    {
      fromJSON(cmd_args[1])
    },
    error = function(e) {
      stop("Failed to parse JSON arguments: ", e$message)
    }
  )
}

# Validate and prepare data
if (exists("validate_json_input") && is.function(validate_json_input)) {
  # Most scripts require data, validate generically
  required_fields <- if ("data" %in% names(args)) c("data") else character(0)
  args <- validate_json_input(args, required = required_fields)
}

# Prepare data variable if needed
if ("data" %in% names(args)) {
  # Convert data to proper data.frame format
  if (is.list(args$data) && !is.data.frame(args$data)) {
    # Handle list format - convert to data.frame
    data <- tryCatch(
      {
        as.data.frame(args$data)
      },
      error = function(e) {
        stop("Failed to convert data to data.frame: ", e$message)
      }
    )
  } else if (is.data.frame(args$data)) {
    data <- args$data
  } else {
    stop("Data must be a list or data.frame, got: ", class(args$data)[1])
  }
} else if (!exists("data")) {
  # No data provided and none exists
  data <- NULL
}

# === MAIN SCRIPT LOGIC ===
{{ MAIN_SCRIPT }}

# === AUTOMATIC OUTPUT HANDLING ===
# Output results in standard JSON format
if (exists("result")) {
  if (exists("format_json_output") && is.function(format_json_output)) {
    cat(safe_json(format_json_output(result)))
  } else {
    cat(jsonlite::toJSON(result, auto_unbox = TRUE))
  }
} else {
  error_msg <- list(error = "No result generated", success = FALSE)
  if (exists("safe_json") && is.function(safe_json)) {
    cat(safe_json(error_msg))
  } else {
    cat(jsonlite::toJSON(error_msg, auto_unbox = TRUE))
  }
}
