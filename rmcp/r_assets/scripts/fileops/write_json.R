# JSON File Writing Script for RMCP
# ==================================
#
# This script writes data to JSON files using jsonlite package with
# support for column-wise formatting and pretty printing options.

# Check and load required packages

# Load required libraries
library(jsonlite)

# Determine script directory for path resolution
script_dir <- if (exists("testthat_testing") && testthat_testing) {
    # Running under testthat - use relative path from test directory
    file.path("..", "..", "R")
} else {
    # Try multiple possible paths for utils.R
    possible_paths <- c(
        file.path("..", "..", "R"),  # Normal relative path
        file.path(getwd(), "rmcp", "r_assets", "R"),  # From project root
        file.path(getwd(), "R"),  # Direct R directory
        "/workspace/rmcp/r_assets/R"  # Docker path
    )
    
    # Try to add script-relative path if possible
    tryCatch({
        script_location <- sys.frame(1)$ofile
        if (!is.null(script_location)) {
            script_based_path <- file.path(dirname(script_location), "..", "..", "R")
            possible_paths <- c(possible_paths, script_based_path)
        }
    }, error = function(e) {
        # sys.frame() not available or no calling frame - continue without it
    })
    
    # Find the first path that contains utils.R
    found_path <- NULL
    for (path in possible_paths) {
        if (file.exists(file.path(path, "utils.R"))) {
            found_path <- path
            break
        }
    }
    
    if (is.null(found_path)) {
        file.path("..", "..", "R")  # Fallback to default
    } else {
        found_path
    }
}

# Load RMCP utilities
utils_path <- file.path(script_dir, "utils.R")
if (file.exists(utils_path)) {
    source(utils_path)
} else {
    stop("Cannot find RMCP utilities at: ", utils_path)
}

# Parse command line arguments
if (!exists("args")) {
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
}


# Validate input
args <- validate_json_input(args, required = c("data"))

# Main script logic
if (!require(jsonlite, quietly = TRUE)) {
    stop("Package 'jsonlite' is required but not installed. Please install it with: install.packages('jsonlite')")
}

# Prepare data and parameters
data <- args$data
file_path <- args$file_path
pretty_print <- args$pretty %||% TRUE
auto_unbox <- args$auto_unbox %||% TRUE

# Convert data to column-wise format (consistent with other RMCP tools)
if (is.data.frame(data)) {
    data_list <- as.list(data)
} else {
    data_list <- data
}

# Write JSON file
write_json(
    data_list, 
    file_path, 
    pretty = pretty_print,
    auto_unbox = auto_unbox
)

# Verify file was written
if (!file.exists(file_path)) {
    stop(paste("Failed to write JSON file:", file_path))
}

file_info <- file.info(file_path)

result <- list(
    file_path = file_path,
    rows_written = if(is.data.frame(data)) nrow(data) else if(is.list(data)) length(data) else 1,
    cols_written = if(is.data.frame(data)) ncol(data) else if(is.list(data)) length(data) else 1,
    variables_written = names(data_list),
    file_size_bytes = file_info$size,
    pretty_formatted = pretty_print,
    success = TRUE,
    timestamp = as.character(Sys.time())
)
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
