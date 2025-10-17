# Stationarity Testing Script for RMCP
# =====================================
#
# This script performs stationarity tests on time series data using
# Augmented Dickey-Fuller, KPSS, or Phillips-Perron tests.


# Load required libraries
library(tseries)


# Prepare data and parameters
test_type <- args$test %||% "adf"

# Extract values from data
if ("values" %in% names(args)) {
  values <- args$values
} else if ("value_col" %in% names(args)) {
  value_col <- args$value_col
  if (value_col %in% names(data)) {
    values <- data[[value_col]]
  } else {
    # Find first numeric column
    numeric_cols <- names(data)[sapply(data, is.numeric)]
    if (length(numeric_cols) > 0) {
      values <- data[[numeric_cols[1]]]
    } else {
      stop("No numeric columns found for stationarity test")
    }
  }
} else {
  # Find first numeric column
  numeric_cols <- names(data)[sapply(data, is.numeric)]
  if (length(numeric_cols) > 0) {
    values <- data[[numeric_cols[1]]]
  } else {
    stop("No numeric columns found for stationarity test")
  }
}

ts_data <- ts(values)

if (test_type == "adf") {
  test_result <- adf.test(ts_data)
  test_name <- "Augmented Dickey-Fuller"
} else if (test_type == "kpss") {
  test_result <- kpss.test(ts_data)
  test_name <- "KPSS"
} else if (test_type == "pp") {
  test_result <- pp.test(ts_data)
  test_name <- "Phillips-Perron"
}

# Handle critical values properly - some tests might not have them
critical_vals <- if (is.null(test_result$critical) || length(test_result$critical) == 0) {
  # Return empty named list to ensure it's treated as object, not array
  structure(list(), names = character(0))
} else {
  as.list(test_result$critical)
}
result <- list(
  test_name = test_name,
  test_type = test_type,
  statistic = as.numeric(test_result$statistic),
  p_value = test_result$p.value,
  critical_values = critical_vals,
  alternative = test_result$alternative,
  is_stationary = if (test_type == "kpss") test_result$p.value > 0.05 else test_result$p.value < 0.05,
  n_obs = length(values),
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = format_result_table(test_result, paste0(test_name, " Test Results")),
    interpretation = paste0(
      test_name, " test: ",
      get_significance(test_result$p.value),
      if (test_type == "kpss") {
        if (test_result$p.value > 0.05) " - series appears stationary" else " - series appears non-stationary"
      } else {
        if (test_result$p.value < 0.05) " - series appears stationary" else " - series appears non-stationary"
      }
    )
  )
)
