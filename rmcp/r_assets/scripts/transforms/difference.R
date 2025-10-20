# Variable Differencing Script for RMCP
# ======================================
#
# This script computes differences of variables for achieving stationarity
# in time series analysis, with optional log transformation.

# Load required libraries
library(knitr)

# Prepare data and parameters
variables <- args$variables
differences <- args$differences %||% 1
diff_order <- differences # For backward compatibility
log_transform <- args$log_transform %||% FALSE

# Load required libraries
result_data <- data

for (var in variables) {
  original_values <- data[[var]]

  # Log transform first if requested
  if (log_transform) {
    if (any(original_values <= 0, na.rm = TRUE)) {
      stop(paste(
        "Cannot log-transform", var, "- contains non-positive values"
      ))
    }
    transformed <- log(original_values)
    log_var <- paste0("log_", var)
    result_data[[log_var]] <- transformed
    working_values <- transformed
    base_name <- log_var
  } else {
    working_values <- original_values
    base_name <- var
  }
  # Compute differences
  diff_values <- working_values
  for (i in 1:diff_order) {
    diff_values <- diff(diff_values)
    diff_name <- paste0(base_name, "_diff", if (diff_order > 1) i else "")
    # Pad with NA to maintain same length
    padded_diff <- c(rep(NA, i), diff_values)
    result_data[[diff_name]] <- padded_diff
  }
}
# Ensure variables_differenced is always an array
diff_vars <- if (length(variables) == 0) character(0) else variables
result <- list(
  data = as.list(result_data),
  variables_differenced = I(as.character(diff_vars)),
  difference_order = diff_order,
  log_transformed = log_transform,
  n_obs = nrow(result_data),
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Create differencing summary table
        diff_summary <- data.frame(
          Operation = "Differencing",
          Variables = length(variables),
          Order = diff_order,
          Log_Transformed = log_transform,
          Observations = nrow(result_data)
        )
        paste(as.character(knitr::kable(
          diff_summary,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        "Variable differences computed successfully"
      }
    ),
    interpretation = paste0(
      "Applied ", diff_order, "-order differencing to ", length(variables),
      " variables", if (log_transform) " (with log transformation)" else "."
    )
  )
)
