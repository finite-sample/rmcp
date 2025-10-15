# Excel File Writing Script for RMCP
# ===================================
#
# This script writes data to Excel files using openxlsx package with
# support for sheet names, row names, and formatting options.

# Load required libraries
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
