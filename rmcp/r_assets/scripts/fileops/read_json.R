# JSON File Reading Script for RMCP
# =================================
#
# This script reads JSON files and converts them to tabular format with support
# for nested structures, arrays, and URL sources.

# Load required libraries
library(dplyr)

# Prepare parameters
file_path <- args$file_path
flatten_data <- args$flatten %||% TRUE
max_depth <- args$max_depth %||% 3
array_to_rows <- args$array_to_rows %||% TRUE

# Check if file exists
if (!file.exists(file_path)) {
  stop(paste("File not found:", file_path))
}

# Check if it's a URL
if (grepl("^https?://", file_path)) {
  # Read from URL
  json_data <- fromJSON(file_path, flatten = flatten_data)
} else {
  # Read from local file
  json_data <- fromJSON(file_path, flatten = flatten_data)
}
# Convert to data frame if possible
if (is.list(json_data) && !is.data.frame(json_data)) {
  # Try to convert list to data frame
  if (all(sapply(json_data, length) == length(json_data[[1]]))) {
    # All elements same length - can convert directly
    data <- as.data.frame(json_data, stringsAsFactors = FALSE)
  } else {
    # Unequal lengths - need to flatten differently
    data <- json_data %>%
      as.data.frame(stringsAsFactors = FALSE)
  }
} else if (is.data.frame(json_data)) {
  data <- json_data
} else {
  # Create single-column data frame
  data <- data.frame(value = json_data, stringsAsFactors = FALSE)
}
# Get file info
if (!grepl("^https?://", file_path)) {
  file_info <- file.info(file_path)
  file_size <- file_info$size
  modified_date <- as.character(file_info$mtime)
} else {
  file_size <- NA
  modified_date <- NA
}
result <- list(
  data = as.list(data), # Convert to column-wise format for schema compatibility
  file_info = list(
    file_path = file_path,
    rows = nrow(data),
    columns = ncol(data),
    column_names = colnames(data),
    file_size_bytes = file_size,
    modified_date = modified_date,
    is_url = grepl("^https?://", file_path)
  ),
  summary = list(
    rows_read = nrow(data),
    columns_read = ncol(data),
    column_types = as.list(sapply(data, class)),
    missing_values = as.list(sapply(data, function(x) sum(is.na(x)))),
    sample_data = if (nrow(data) > 0) head(data, 3) else data.frame()
  )
)
