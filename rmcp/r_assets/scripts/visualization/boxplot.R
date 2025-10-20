# Boxplot Visualization Script for RMCP
# ======================================
#
# This script creates boxplots for quartile analysis and outlier detection.

# Load required libraries
options(repos = c(CRAN = "https://cloud.r-project.org/"))
library(ggplot2)
library(rlang)

# Prepare data and parameters
variable <- args$variable
group_var <- if (!is.null(args$group) && length(args$group) > 0 && args$group != "" && !identical(args$group, list())) args$group else NA
title <- args$title %||% paste("Boxplot of", variable)
file_path <- args$file_path
return_image <- args$return_image %||% TRUE
width <- args$width %||% 800
height <- args$height %||% 600

# Create base plot
if (!is.null(group_var) && !is.na(group_var)) {
  p <- ggplot(data, aes(x = !!sym(group_var), y = !!sym(variable), fill = !!sym(group_var))) +
    geom_boxplot(alpha = 0.7) +
    labs(title = title, x = group_var, y = variable)
} else {
  p <- ggplot(data, aes(y = !!sym(variable))) +
    geom_boxplot(fill = "steelblue", alpha = 0.7) +
    labs(title = title, x = "", y = variable)
}
p <- p + theme_minimal() +
  theme(plot.title = element_text(hjust = 0.5))
# Save to file if path provided and not empty
if (!is.null(file_path) && nchar(file_path) > 0) {
  ggsave(file_path, plot = p, width = width / 100, height = height / 100, dpi = 100)
  plot_saved <- file.exists(file_path)
} else {
  plot_saved <- FALSE
}
# Calculate quartile statistics
values <- data[[variable]][!is.na(data[[variable]])]
quartiles <- quantile(values, c(0.25, 0.5, 0.75))
iqr <- quartiles[3] - quartiles[1]
lower_fence <- quartiles[1] - 1.5 * iqr
upper_fence <- quartiles[3] + 1.5 * iqr
outliers <- values[values < lower_fence | values > upper_fence]
stats <- list(
  q1 = quartiles[1],
  median = quartiles[2],
  q3 = quartiles[3],
  iqr = iqr,
  lower_fence = lower_fence,
  upper_fence = upper_fence,
  outliers_count = length(outliers),
  outlier_percentage = length(outliers) / length(values) * 100
)
# Prepare result
result <- list(
  plot_type = "boxplot",
  variable = variable,
  group_variable = group_var,
  statistics = stats,
  title = title,
  n_obs = length(values),
  plot_saved = plot_saved
)
# Add file path if provided and not empty
if (!is.null(file_path) && nchar(file_path) > 0) {
  result$file_path <- file_path
}
# Generate base64 image if requested
if (return_image) {
  image_data <- if (exists("safe_encode_plot")) {
    safe_encode_plot(p, width, height)
  } else {
    "Plot created successfully but base64 encoding not available in standalone mode"
  }
  result$image_data <- image_data
}
