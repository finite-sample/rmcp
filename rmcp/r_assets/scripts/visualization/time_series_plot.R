# Time Series Plot Visualization Script for RMCP
# ===============================================
#
# This script creates time series plots for trend analysis with forecasting visualization.

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
time_var <- args$time_variable
variables <- args$variables
title <- args$title %||% "Time Series Plot"
file_path <- args$file_path
return_image <- args$return_image %||% TRUE
width <- args$width %||% 800
height <- args$height %||% 600

# Convert time variable
if (is.character(data[[time_var]])) {
  data[[time_var]] <- as.Date(data[[time_var]])
} else if (is.numeric(data[[time_var]])) {
  data$time_index <- data[[time_var]]
}

# Reshape data for multiple variables
if (length(variables) > 1) {
  # Melt data for multiple series
  library(reshape2)
  melted_data <- melt(data, id.vars = time_var, measure.vars = variables)
  p <- ggplot(melted_data, aes_string(x = time_var, y = "value", color = "variable")) +
    geom_line(size = 1) +
    geom_point(alpha = 0.6) +
    labs(title = title, x = time_var, y = "Value", color = "Variable")
} else {
  # Single variable plot
  p <- ggplot(data, aes_string(x = time_var, y = variables[1])) +
    geom_line(color = "steelblue", size = 1) +
    geom_point(alpha = 0.6, color = "steelblue") +
    labs(title = title, x = time_var, y = variables[1])
}

p <- p + theme_minimal() +
  theme(
    plot.title = element_text(hjust = 0.5),
    axis.text.x = element_text(angle = 45, hjust = 1)
  )

# Save to file if path provided
if (!is.null(file_path)) {
  ggsave(file_path, plot = p, width = width / 100, height = height / 100, dpi = 100)
  plot_saved <- file.exists(file_path)
} else {
  plot_saved <- FALSE
}

# Calculate basic time series statistics
n_obs <- nrow(data)
date_range <- if (is.Date(data[[time_var]])) {
  list(start = min(data[[time_var]], na.rm = TRUE), end = max(data[[time_var]], na.rm = TRUE))
} else {
  list(start = min(data[[time_var]], na.rm = TRUE), end = max(data[[time_var]], na.rm = TRUE))
}

# Prepare result
result <- list(
  plot_type = "time_series",
  time_variable = time_var,
  variables = variables,
  date_range = date_range,
  title = title,
  n_obs = n_obs,
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
