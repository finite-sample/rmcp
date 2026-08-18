# Regression Diagnostic Plot Visualization Script for RMCP
# ========================================================
#
# This script creates comprehensive 4-panel diagnostic plots for model validation.

# Load required libraries
options(repos = c(CRAN = "https://cloud.r-project.org/"))
library(ggplot2)
library(gridExtra)
library(rlang)
library(knitr)

# Prepare data and parameters
formula_str <- args$formula
title <- args$title %||% "Regression Diagnostic Plots"
file_path <- args$file_path
return_image <- args$return_image %||% TRUE
residual_plots <- args$residual_plots %||% TRUE
width <- args$width %||% 800
height <- args$height %||% 600

# Fit regression model
formula <- as.formula(formula_str)
model <- lm(formula, data = data)

# Extract model information
fitted_vals <- fitted(model)
residuals_vals <- residuals(model)
std_residuals <- rstandard(model)
actual_vals <- model.response(model.frame(model))
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
# Combine plots using arrangeGrob with null graphics device
pdf(file = NULL) # Create null device for layout calculations
if (residual_plots) {
  combined_plot <- arrangeGrob(p1, p2, p3, p4, ncol = 2, top = title)
} else {
  combined_plot <- ggplot(
    data.frame(actual = actual_vals, fitted = fitted_vals),
    aes(x = actual, y = fitted)
  ) +
    geom_point(alpha = 0.7) +
    geom_abline(slope = 1, intercept = 0, color = "red", linetype = "dashed") +
    labs(title = title, x = "Actual", y = "Fitted") +
    theme_minimal()
}
dev.off() # Close null device
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
# Prepare result
result <- list(
  plot_type = "regression_plot",
  r_squared = r_squared,
  adj_r_squared = adj_r_squared,
  residual_se = model_summary$sigma,
  formula = formula_str,
  residual_plots = residual_plots,
  n_obs = nobs(model),
  dimensions = list(width = width, height = height)
)
# Add file path if provided
if (!is.null(file_path)) {
  result$file_path <- file_path
}
# Generate base64 image if requested
if (return_image) {
  image_data <- if (exists("safe_encode_plot")) {
    safe_encode_plot(combined_plot, width, height)
  } else {
    "Plot created successfully but base64 encoding not available in standalone mode"
  }
  result$image_data <- image_data
}
