# JSON File Writing Script for RMCP
# ==================================
#
# This script writes data to JSON files using jsonlite package with
# support for column-wise formatting and pretty printing options.

# Load required libraries
if (!require(jsonlite, quietly = TRUE)) {
  stop("Package 'jsonlite' is required but not installed. Please install it with: install.packages('jsonlite')")
}

# Prepare data and parameters - handle both template and standalone data passing
if (exists("data") && !is.null(data)) {
  # Data already loaded from template system or standalone
} else if ("data" %in% names(args)) {
  data <- args$data
} else {
  stop("No data provided")
}

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
  rows_written = if (is.data.frame(data)) nrow(data) else if (is.list(data)) length(data) else 1,
  cols_written = if (is.data.frame(data)) ncol(data) else if (is.list(data)) length(data) else 1,
  variables_written = names(data_list),
  file_size_bytes = file_info$size,
  pretty_formatted = pretty_print,
  success = TRUE,
  timestamp = as.character(Sys.time())
)
