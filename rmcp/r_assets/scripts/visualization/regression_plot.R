# Regression Diagnostic Plot Visualization Script for RMCP
# ========================================================
#
# This script creates comprehensive 4-panel diagnostic plots for model validation.

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
library(gridExtra)

# Prepare data and parameters
formula_str <- args$formula
title <- args$title %||% "Regression Diagnostic Plots"
file_path <- args$file_path
return_image <- args$return_image %||% TRUE
width <- args$width %||% 800
height <- args$height %||% 600

# Fit regression model
formula <- as.formula(formula_str)
model <- lm(formula, data = data)

# Extract model information
fitted_vals <- fitted(model)
residuals_vals <- residuals(model)
std_residuals <- rstandard(model)
response_var <- all.vars(formula)[1]
actual_vals <- data[[response_var]]

# Create diagnostic plots
# 1. Residuals vs Fitted
p1 <- ggplot(
  data.frame(fitted = fitted_vals, residuals = residuals_vals),
  aes(x = fitted, y = residuals)
) +
  geom_point(alpha = 0.6) +
  geom_hline(yintercept = 0, color = "red", linetype = "dashed") +
  geom_smooth(se = FALSE, color = "blue") +
  labs(title = "Residuals vs Fitted", x = "Fitted Values", y = "Residuals") +
  theme_minimal()

# 2. Q-Q Plot
p2 <- ggplot(data.frame(sample = std_residuals), aes(sample = sample)) +
  stat_qq() +
  stat_qq_line(color = "red") +
  labs(title = "Q-Q Plot", x = "Theoretical Quantiles", y = "Sample Quantiles") +
  theme_minimal()

# 3. Scale-Location Plot
p3 <- ggplot(
  data.frame(fitted = fitted_vals, sqrt_std_res = sqrt(abs(std_residuals))),
  aes(x = fitted, y = sqrt_std_res)
) +
  geom_point(alpha = 0.6) +
  geom_smooth(se = FALSE, color = "red") +
  labs(title = "Scale-Location", x = "Fitted Values", y = "√|Standardized Residuals|") +
  theme_minimal()

# 4. Residuals vs Leverage
leverage_vals <- hatvalues(model)
p4 <- ggplot(
  data.frame(leverage = leverage_vals, std_residuals = std_residuals),
  aes(x = leverage, y = std_residuals)
) +
  geom_point(alpha = 0.6) +
  geom_smooth(se = FALSE, color = "red") +
  labs(title = "Residuals vs Leverage", x = "Leverage", y = "Standardized Residuals") +
  theme_minimal()

# Combine plots
combined_plot <- grid.arrange(p1, p2, p3, p4, ncol = 2, top = title)

# Save to file if path provided
if (!is.null(file_path)) {
  ggsave(file_path, plot = combined_plot, width = width / 100, height = height / 100, dpi = 100)
  plot_saved <- file.exists(file_path)
} else {
  plot_saved <- FALSE
}

# Calculate diagnostic statistics
model_summary <- summary(model)
r_squared <- model_summary$r.squared
adj_r_squared <- model_summary$adj.r.squared
f_statistic <- model_summary$fstatistic[1]
p_value <- pf(f_statistic, model_summary$fstatistic[2], model_summary$fstatistic[3], lower.tail = FALSE)

diagnostics <- list(
  r_squared = r_squared,
  adj_r_squared = adj_r_squared,
  f_statistic = f_statistic,
  p_value = p_value,
  residual_se = model_summary$sigma,
  n_obs = nobs(model),
  degrees_freedom = model_summary$df[2]
)

# Prepare result
result <- list(
  plot_type = "regression_plot",
  formula = formula_str,
  model_summary = diagnostics,
  title = title,
  plot_saved = plot_saved
)

# Add file path if provided
if (!is.null(file_path)) {
  result$file_path <- file_path
}

# Generate base64 image if requested
if (return_image) {
  image_data <- safe_encode_plot(combined_plot, width, height)
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
