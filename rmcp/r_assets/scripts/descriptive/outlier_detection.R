# Outlier Detection Analysis Script for RMCP
# ==========================================
#
# This script detects outliers in numeric data using multiple methods:
# IQR (Interquartile Range), Z-score, and Modified Z-score approaches.

# Load required libraries
library(knitr)

# Prepare data and parameters
variable <- args$variable
method <- args$method %||% "iqr"
threshold <- args$threshold %||% 1.5

# Load required libraries
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
        paste(as.character(knitr::kable(
          outlier_df,
          format = "markdown", digits = 4
        )), collapse = "\n")
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
