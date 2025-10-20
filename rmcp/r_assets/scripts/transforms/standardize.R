# Variable Standardization Script for RMCP
# =========================================
#
# This script standardizes variables using different scaling methods:
# z-score, min-max, or robust scaling for data preprocessing.

# Load required libraries
library(knitr)

# Prepare data and parameters
variables <- args$variables
method <- args$method %||% "z_score"

# Load required libraries
result_data <- data
scaling_info <- list()

for (var in variables) {
  original_values <- data[[var]]

  if (method == "z_score") {
    mean_val <- mean(original_values, na.rm = TRUE)
    sd_val <- sd(original_values, na.rm = TRUE)
    scaled <- (original_values - mean_val) / sd_val
    scaling_info[[var]] <- list(mean = mean_val, sd = sd_val)
  } else if (method == "min_max") {
    min_val <- min(original_values, na.rm = TRUE)
    max_val <- max(original_values, na.rm = TRUE)
    scaled <- (original_values - min_val) / (max_val - min_val)
    scaling_info[[var]] <- list(min = min_val, max = max_val)
  } else if (method == "robust") {
    median_val <- median(original_values, na.rm = TRUE)
    mad_val <- mad(original_values, na.rm = TRUE)
    scaled <- (original_values - median_val) / mad_val
    scaling_info[[var]] <- list(median = median_val, mad = mad_val)
  }
  new_var <- paste0(var, "_", method)
  result_data[[new_var]] <- scaled
}
result <- list(
  data = as.list(result_data),
  scaling_method = method,
  scaling_info = scaling_info,
  variables_scaled = variables,
  n_obs = nrow(result_data),
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Create standardization summary table
        std_summary <- data.frame(
          Operation = "Standardization",
          Method = method,
          Variables = length(variables),
          Observations = nrow(result_data)
        )
        paste(as.character(knitr::kable(
          std_summary,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        "Variables standardized successfully"
      }
    ),
    interpretation = paste0("Standardized ", length(variables), " variables using ", method, " method.")
  )
)
