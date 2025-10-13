# Outlier Detection Analysis Script for RMCP
# ==========================================
#
# This script detects outliers in numeric data using multiple methods:
# IQR (Interquartile Range), Z-score, and Modified Z-score approaches.

# Prepare data and parameters

# Load required libraries
library(jsonlite)

# Determine script directory for path resolution
script_dir <- if (exists("testthat_testing") && testthat_testing) {
  # Running under testthat - use relative path from test directory
  file.path("..", "..", "R")
} else {
  # Running normally - use relative path from script location
  file.path("..", "..", "R")
}

# Load RMCP utilities
utils_path <- file.path(script_dir, "utils.R")
if (file.exists(utils_path)) {
  source(utils_path)
} else {
  stop("Cannot find RMCP utilities at: ", utils_path)
}

# Parse command line arguments
args <- if (exists("test_args")) {
  # Use test arguments if provided (for testthat)
  test_args
} else {
  # Parse from command line
  cmd_args <- commandArgs(trailingOnly = TRUE)
  if (length(cmd_args) == 0) {
    stop("No JSON arguments provided")
  }

  # Parse JSON input
  tryCatch(
    {
      fromJSON(cmd_args[1])
    },
    error = function(e) {
      stop("Failed to parse JSON arguments: ", e$message)
    }
  )
}


# Validate input
args <- validate_json_input(args, required = c("data"))

# Main script logic
variable <- args$variable
method <- args$method %||% "iqr"
threshold <- args$threshold %||% 3.0

values <- data[[variable]]
values_clean <- values[!is.na(values)]

if (method == "iqr") {
  Q1 <- quantile(values_clean, 0.25)
  Q3 <- quantile(values_clean, 0.75)
  IQR <- Q3 - Q1
  lower_bound <- Q1 - 1.5 * IQR
  upper_bound <- Q3 + 1.5 * IQR
  outliers <- which(values < lower_bound | values > upper_bound)
  bounds <- list(lower = lower_bound, upper = upper_bound, iqr = IQR)
} else if (method == "z_score") {
  mean_val <- mean(values_clean)
  sd_val <- sd(values_clean)
  z_scores <- abs((values - mean_val) / sd_val)
  outliers <- which(z_scores > threshold)
  bounds <- list(threshold = threshold, mean = mean_val, sd = sd_val)
} else if (method == "modified_z") {
  median_val <- median(values_clean)
  mad_val <- mad(values_clean)
  modified_z <- abs(0.6745 * (values - median_val) / mad_val)
  outliers <- which(modified_z > threshold)
  bounds <- list(threshold = threshold, median = median_val, mad = mad_val)
}

result <- list(
  method = method,
  outlier_indices = outliers,
  outlier_values = values[outliers],
  n_outliers = length(outliers),
  n_obs = length(values[!is.na(values)]),
  outlier_percentage = length(outliers) / length(values_clean) * 100,
  bounds = bounds,
  variable = variable,

  # Special non-validated field for formatting (using assignment instead of backticks)
  "_formatting" = list(
    summary = tryCatch(
      {
        # Create outlier summary table
        outlier_df <- data.frame(
          Method = method,
          Variable = variable,
          Outliers_Detected = length(outliers),
          Total_Observations = length(values_clean),
          Outlier_Percentage = round(length(outliers) / length(values_clean) * 100, 2)
        )
        as.character(knitr::kable(
          outlier_df,
          format = "markdown", digits = 4
        ))
      },
      error = function(e) {
        "Outlier detection completed successfully"
      }
    ),
    interpretation = paste0(
      "Detected ", length(outliers), " outliers (",
      round(length(outliers) / length(values_clean) * 100, 1),
      "% of observations) using ", method, " method."
    )
  )
)
# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
