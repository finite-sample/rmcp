# Excel File Writing Script for RMCP
# ===================================
#
# This script writes data to Excel files using openxlsx package with
# support for sheet names, row names, and formatting options.

# Check and load required packages

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
    tryCatch({
        fromJSON(cmd_args[1])
    }, error = function(e) {
        stop("Failed to parse JSON arguments: ", e$message)
    })
}


# Validate input
args <- validate_json_input(args, required = c("data"))

# Main script logic
if (!require(openxlsx, quietly = TRUE)) {
    stop("Package 'openxlsx' is required but not installed. Please install it with: install.packages('openxlsx')")
}

# Prepare data and parameters
file_path <- args$file_path
sheet_name <- args$sheet_name %||% "Sheet1"
include_rownames <- args$include_rownames %||% FALSE

# Create workbook and add worksheet
wb <- createWorkbook()
addWorksheet(wb, sheet_name)

# Write data to worksheet
writeData(wb, sheet_name, data, rowNames = include_rownames)

# Save workbook
saveWorkbook(wb, file_path, overwrite = TRUE)

# Verify file was written
if (!file.exists(file_path)) {
    stop(paste("Failed to write Excel file:", file_path))
}

file_info <- file.info(file_path)

result <- list(
    file_path = file_path,
    sheet_name = sheet_name,
    rows_written = nrow(data),
    cols_written = ncol(data), 
    file_size_bytes = file_info$size,
    success = TRUE,
    timestamp = as.character(Sys.time())
)
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
