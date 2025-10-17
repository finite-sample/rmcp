# Scatter Plot Visualization Script for RMCP
# ===========================================
#
# This script creates scatter plots with optional grouping and trend lines
# using ggplot2 for publication-quality visualizations.

# Set CRAN mirror
# Load required libraries
options(repos = c(CRAN = "https://cloud.r-project.org/"))
library(ggplot2)
library(rlang)

# Prepare data and parameters with safe fallbacks
x_var <- args$x
y_var <- args$y
group_var <- if (!is.null(args$group) && length(args$group) > 0 &&
  args$group != "" && !identical(args$group, list())) {
  args$group
} else {
  NA
}
title <- args$title %||% paste("Scatter plot:", y_var, "vs", x_var)
file_path <- args$file_path
return_image <- args$return_image %||% TRUE
width <- args$width %||% 800
height <- args$height %||% 600

# Create base plot using modern aes() syntax
p <- ggplot(data, aes(x = !!sym(x_var), y = !!sym(y_var)))
if (!is.null(group_var) && !is.na(group_var)) {
  p <- p + geom_point(aes(color = !!sym(group_var)), alpha = 0.7) +
    geom_smooth(aes(color = !!sym(group_var)), method = "lm", se = TRUE)
} else {
  p <- p + geom_point(alpha = 0.7) +
    geom_smooth(method = "lm", se = TRUE, color = "blue")
}
p <- p + labs(title = title, x = x_var, y = y_var) +
  theme_minimal() +
  theme(plot.title = element_text(hjust = 0.5))
# Save to file if path provided
if (!is.null(file_path)) {
  ggsave(file_path, plot = p, width = width / 100, height = height / 100, dpi = 100)
  plot_saved <- file.exists(file_path)
} else {
  plot_saved <- FALSE
}
# Basic correlation
correlation <- cor(data[[x_var]], data[[y_var]], use = "complete.obs")
# Prepare result
result <- list(
  plot_type = "scatter",
  variables = list(
    x = x_var,
    y = y_var,
    group = group_var
  ),
  statistics = list(
    correlation = correlation,
    n_points = sum(!is.na(data[[x_var]]) & !is.na(data[[y_var]]))
  ),
  title = title,
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
