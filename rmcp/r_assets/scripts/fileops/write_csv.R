# CSV File Writing Script for RMCP
# ================================
#
# This script writes data to CSV files with formatting options including
# row names, missing value representation, and append mode support.

# Prepare data and parameters
file_path <- args$file_path
include_rownames <- args$include_rownames %||% FALSE
na_string <- args$na_string %||% ""
append_mode <- args$append %||% FALSE

# Write CSV
write.csv(data, file_path, row.names = include_rownames, na = na_string, append = append_mode)

# Verify file was written
if (!file.exists(file_path)) {
  stop(paste("Failed to write file:", file_path))
}

file_info <- file.info(file_path)

result <- list(
  file_path = file_path,
  rows_written = nrow(data),
  cols_written = ncol(data),
  file_size_bytes = file_info$size,
  success = TRUE,
  timestamp = as.character(Sys.time())
)
