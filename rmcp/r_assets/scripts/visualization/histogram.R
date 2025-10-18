# Histogram Visualization Script for RMCP
# ========================================
#
# This script creates histograms with density overlays for distribution analysis.

# Load required libraries
options(repos = c(CRAN = "https://cloud.r-project.org/"))
library(ggplot2)
library(rlang)

# Prepare data and parameters
variable <- args$variable
group_var <- if (!is.null(args$group) && length(args$group) > 0 && args$group != "" && !identical(args$group, list())) args$group else NA
bins <- args$bins %||% 30
title <- args$title %||% paste("Histogram of", variable)
file_path <- args$file_path
return_image <- args$return_image %||% TRUE
width <- args$width %||% 800
height <- args$height %||% 600

# Create base plot
p <- ggplot(data, aes(x = !!sym(variable)))
if (!is.null(group_var) && !is.na(group_var)) {
  p <- p + geom_histogram(aes(fill = !!sym(group_var)), bins = bins, alpha = 0.7, position = "identity") +
    geom_density(aes(color = !!sym(group_var)), alpha = 0.8)
} else {
  p <- p + geom_histogram(bins = bins, alpha = 0.7, fill = "steelblue") +
    geom_density(alpha = 0.8, color = "red")
}
p <- p + labs(title = title, x = variable, y = "Frequency") +
  theme_minimal() +
  theme(plot.title = element_text(hjust = 0.5))
# Save to file if path provided
if (!is.null(file_path)) {
  ggsave(file_path, plot = p, width = width / 100, height = height / 100, dpi = 100)
  plot_saved <- file.exists(file_path)
} else {
  plot_saved <- FALSE
}
# Basic statistics
values <- data[[variable]][!is.na(data[[variable]])]
stats <- list(
  mean = mean(values),
  median = median(values),
  sd = sd(values),
  skewness = (sum((values - mean(values))^3) / length(values)) / (sd(values)^3),
  kurtosis = (sum((values - mean(values))^4) / length(values)) / (sd(values)^4) - 3
)
# Prepare result
result <- list(
  plot_type = "histogram",
  variable = variable,
  group_variable = group_var,
  bins = bins,
  statistics = stats,
  title = title,
  n_obs = length(values),
  plot_saved = plot_saved
)
# Add file path if provided
if (!is.null(file_path)) {
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
