# Excel File Reading Script for RMCP
# ==================================
#
# This script reads Excel files (.xlsx, .xls) with flexible sheet and range selection.
# Supports multiple sheets, custom ranges, and comprehensive file metadata.


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


# Main script logic
library(readxl)

# Prepare parameters
file_path <- args$file_path
sheet_name <- args$sheet_name
header <- args$header %||% TRUE
skip_rows <- args$skip_rows %||% 0
max_rows <- args$max_rows
cell_range <- args$cell_range
na_strings <- args$na_strings %||% c("", "NA", "NULL")

# Check if file exists
if (!file.exists(file_path)) {
    stop(paste("File not found:", file_path))
}

# Check file extension
file_ext <- tolower(tools::file_ext(file_path))
if (!file_ext %in% c("xlsx", "xls")) {
    stop("File must be .xlsx or .xls format")
}

# Get sheet information
sheet_names <- excel_sheets(file_path)

# Determine which sheet to read
if (is.null(sheet_name)) {
    sheet_to_read <- 1  # Default to first sheet
    actual_sheet_name <- sheet_names[1]
} else {
    if (is.numeric(sheet_name)) {
        sheet_to_read <- as.integer(sheet_name)
        actual_sheet_name <- sheet_names[sheet_to_read]
    } else {
        if (sheet_name %in% sheet_names) {
            sheet_to_read <- sheet_name
            actual_sheet_name <- sheet_name
        } else {
            stop(paste("Sheet not found:", sheet_name, ". Available sheets:", paste(sheet_names, collapse=", ")))
        }
    }
}

# Read Excel file with parameters
read_args <- list(
    path = file_path,
    sheet = sheet_to_read,
    col_names = header,
    skip = skip_rows,
    na = na_strings
)

# Add optional parameters
if (!is.null(max_rows)) {
    read_args$n_max <- max_rows
}
if (!is.null(cell_range)) {
    read_args$range <- cell_range
}

# Read the data
data <- do.call(read_excel, read_args)

# Convert to data frame
data <- as.data.frame(data)

# Get file info
file_info <- file.info(file_path)

result <- list(
    data = data,
    file_info = list(
        file_path = file_path,
        sheet_name = actual_sheet_name,
        available_sheets = sheet_names,
        rows = nrow(data),
        columns = ncol(data),
        column_names = colnames(data),
        file_size_bytes = file_info$size,
        modified_date = as.character(file_info$mtime)
    ),
    summary = list(
        rows_read = nrow(data),
        columns_read = ncol(data),
        column_types = as.list(sapply(data, class)),
        missing_values = as.list(sapply(data, function(x) sum(is.na(x)))),
        sample_data = if(nrow(data) > 0) head(data, 3) else data.frame()
    )
)
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
