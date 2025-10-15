# CSV File Reading Script for RMCP
# ================================
#
# This script reads CSV files with flexible parsing options including support
# for URLs, custom separators, missing value handling, and file metadata extraction.

# Prepare parameters
file_path <- args$file_path
header <- args$header %||% TRUE
sep <- args$sep %||% ","
na_strings <- args$na_strings %||% c("", "NA", "NULL")
skip_rows <- args$skip_rows %||% 0
max_rows <- args$max_rows

# Check if it's a URL or local file
is_url <- grepl("^https?://", file_path)

if (is_url) {
  # Read from URL
  if (!is.null(max_rows)) {
    data <- read.csv(url(file_path),
      header = header, sep = sep,
      na.strings = na_strings, skip = skip_rows, nrows = max_rows
    )
  } else {
    data <- read.csv(url(file_path),
      header = header, sep = sep,
      na.strings = na_strings, skip = skip_rows
    )
  }
} else {
  # Check if local file exists
  if (!file.exists(file_path)) {
    stop(paste("File not found:", file_path))
  }
  # Read local CSV
  if (!is.null(max_rows)) {
    data <- read.csv(file_path,
      header = header, sep = sep,
      na.strings = na_strings, skip = skip_rows, nrows = max_rows
    )
  } else {
    data <- read.csv(file_path,
      header = header, sep = sep,
      na.strings = na_strings, skip = skip_rows
    )
  }
}
# Data summary
numeric_vars <- names(data)[sapply(data, is.numeric)]
character_vars <- names(data)[sapply(data, is.character)]
factor_vars <- names(data)[sapply(data, is.factor)]
# Get file info if it's a local file
if (!is_url) {
  file_info_obj <- file.info(file_path)
  file_size <- file_info_obj$size
  modified_date <- as.character(file_info_obj$mtime)
} else {
  file_size <- NA
  modified_date <- NA
}
result <- list(
  data = data,
  file_info = list(
    file_path = file_path,
    is_url = is_url,
    n_rows = nrow(data),
    n_cols = ncol(data),
    column_names = names(data),
    numeric_variables = numeric_vars,
    character_variables = character_vars,
    factor_variables = factor_vars,
    file_size_bytes = file_size,
    modified_date = modified_date
  ),
  parsing_info = list(
    header = header,
    separator = sep,
    na_strings = na_strings,
    rows_skipped = skip_rows
  ),
  summary = list(
    rows_read = nrow(data),
    columns_read = ncol(data),
    column_types = as.list(sapply(data, class)),
    missing_values = as.list(sapply(data, function(x) sum(is.na(x)))),
    sample_data = if (nrow(data) > 0) head(data, 3) else data.frame()
  )
)
