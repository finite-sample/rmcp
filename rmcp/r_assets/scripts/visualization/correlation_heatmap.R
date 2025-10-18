# Correlation Heatmap Visualization Script for RMCP
# ==================================================
#
# This script creates correlation heatmaps with color-coded matrices for statistical analysis.

# Load required libraries
options(repos = c(CRAN = "https://cloud.r-project.org/"))
library(ggplot2)
library(reshape2)
library(rlang)

# Prepare data and parameters
variables <- args$variables
method <- args$method %||% "pearson"
title <- args$title %||% paste("Correlation Heatmap -", toupper(method))
file_path <- args$file_path
return_image <- args$return_image %||% TRUE
width <- args$width %||% 800
height <- args$height %||% 600

# Calculate correlation matrix
numeric_data <- data[variables]
cor_matrix <- cor(numeric_data, use = "complete.obs", method = method)

# Melt correlation matrix for ggplot
melted_cor <- melt(cor_matrix)
names(melted_cor) <- c("Var1", "Var2", "Correlation")

# Create heatmap
p <- ggplot(melted_cor, aes(Var1, Var2, fill = Correlation)) +
  geom_tile() +
  scale_fill_gradient2(
    low = "blue", high = "red", mid = "white",
    midpoint = 0, limit = c(-1, 1), space = "Lab"
  ) +
  theme_minimal() +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1),
    plot.title = element_text(hjust = 0.5)
  ) +
  labs(title = title, x = "", y = "") +
  geom_text(aes(label = round(Correlation, 2)), size = 3)
# Save to file if path provided
if (!is.null(file_path)) {
  ggsave(file_path, plot = p, width = width / 100, height = height / 100, dpi = 100)
  plot_saved <- file.exists(file_path)
} else {
  plot_saved <- FALSE
}
# Calculate correlation statistics
cor_values <- cor_matrix[lower.tri(cor_matrix)]
strongest_correlations <- which(abs(cor_matrix) == max(abs(cor_matrix[cor_matrix != 1])), arr.ind = TRUE)
stats <- list(
  method = method,
  mean_correlation = mean(cor_values, na.rm = TRUE),
  max_correlation = max(abs(cor_values), na.rm = TRUE),
  min_correlation = min(abs(cor_values), na.rm = TRUE),
  n_variables = length(variables),
  n_correlations = length(cor_values)
)
# Prepare result
result <- list(
  plot_type = "correlation_heatmap",
  variables = variables,
  correlation_matrix = cor_matrix,
  statistics = stats,
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
