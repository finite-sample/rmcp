# JSON File Writing Script for RMCP
# ==================================
#
# This script writes data to JSON files using jsonlite package with
# support for column-wise formatting and pretty printing options.

# Check and load required packages
if (!require(jsonlite, quietly = TRUE)) {
    stop("Package 'jsonlite' is required but not installed. Please install it with: install.packages('jsonlite')")
}

# Prepare data and parameters
data <- as.data.frame(args$data)
file_path <- args$file_path
pretty_print <- args$pretty %||% TRUE
auto_unbox <- args$auto_unbox %||% TRUE

# Convert data to column-wise format (consistent with other RMCP tools)
data_list <- as.list(data)

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
    rows_written = nrow(data),
    cols_written = ncol(data),
    variables_written = names(data_list),
    file_size_bytes = file_info$size,
    pretty_formatted = pretty_print,
    success = TRUE,
    timestamp = as.character(Sys.time())
)