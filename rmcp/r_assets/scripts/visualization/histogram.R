# Histogram Visualization Script for RMCP
# ========================================
#
# This script creates histograms with density overlays for distribution analysis.

# Set CRAN mirror

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
options(repos = c(CRAN = "https://cloud.r-project.org/"))
library(ggplot2)

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
p <- ggplot(data, aes_string(x = variable))
if (!is.null(group_var)) {
  p <- p + geom_histogram(aes_string(fill = group_var), bins = bins, alpha = 0.7, position = "identity") +
    geom_density(aes_string(color = group_var), alpha = 0.8)
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
  image_data <- safe_encode_plot(p, width, height)
  if (!is.null(image_data)) {
    result$image_data <- image_data
  }
}
# Output results in standard JSON format
if (exists("result")) {
  cat(safe_json(format_json_output(result)))
} else {
  cat(safe_json(list(error = "No result generated", success = FALSE)))
}
