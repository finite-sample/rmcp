# Time Series Decomposition Script for RMCP
# ==========================================
#
# This script decomposes time series into trend, seasonal, and remainder
# components using additive or multiplicative decomposition methods.

# Load required libraries
library(knitr)

# Prepare data and parameters
frequency <- args$frequency %||% 12
decomp_type <- args$type %||% "additive"

# Extract values from data
if ("data" %in% names(args) && "values" %in% names(args$data)) {
  values <- args$data$values
} else if ("values" %in% names(args)) {
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
      stop("No numeric columns found for decomposition")
    }
  }
} else {
  # Find first numeric column
  numeric_cols <- names(data)[sapply(data, is.numeric)]
  if (length(numeric_cols) > 0) {
    values <- data[[numeric_cols[1]]]
  } else {
    stop("No numeric columns found for decomposition")
  }
}

# Create time series
ts_data <- ts(values, frequency = frequency)

# Validate minimum length for decomposition
min_periods <- 2 * frequency
if (length(values) < min_periods) {
  stop(paste("Time series too short for decomposition. Need at least", min_periods, "observations for frequency", frequency))
}

# Decompose
if (decomp_type == "multiplicative") {
  decomp <- decompose(ts_data, type = "multiplicative")
} else {
  decomp <- decompose(ts_data, type = "additive")
}

# Handle NA values properly for JSON - use I() to preserve arrays
result <- list(
  original = I(as.numeric(decomp$x)),
  trend = I(as.numeric(decomp$trend)),
  seasonal = I(as.numeric(decomp$seasonal)),
  remainder = I(as.numeric(decomp$random)),
  type = decomp_type,
  frequency = frequency,
  n_obs = length(values),
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Create decomposition summary table
        decomp_summary <- data.frame(
          Component = c("Original", "Trend", "Seasonal", "Remainder"),
          Missing_Values = c(
            sum(is.na(decomp$x)),
            sum(is.na(decomp$trend)),
            sum(is.na(decomp$seasonal)),
            sum(is.na(decomp$random))
          ),
          Type = c(decomp_type, decomp_type, decomp_type, decomp_type)
        )
        paste(as.character(knitr::kable(
          decomp_summary,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        "Time series decomposition completed successfully"
      }
    ),
    interpretation = paste0("Time series decomposed using ", decomp_type, " method with frequency ", frequency, ".")
  )
)
