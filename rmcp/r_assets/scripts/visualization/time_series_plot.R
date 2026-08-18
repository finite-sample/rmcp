# Time Series Plot Visualization Script for RMCP
# ===============================================
#
# This script creates time series plots for trend analysis with forecasting visualization.

# Load required libraries
options(repos = c(CRAN = "https://cloud.r-project.org/"))
library(ggplot2)
library(rlang)

# Prepare data and parameters
title <- args$title %||% "Time Series Plot"
file_path <- args$file_path
return_image <- args$return_image %||% TRUE
show_trend <- args$show_trend %||% TRUE
width <- args$width %||% 800
height <- args$height %||% 600

# Use the public schema: values are required and dates are optional.
values <- as.numeric(data$values)
has_dates <- "dates" %in% names(data) && !all(is.na(data$dates))
if (has_dates) {
  parsed_dates <- as.Date(data$dates)
  if (any(is.na(parsed_dates))) {
    stop("dates must contain valid ISO 8601 calendar dates")
  }
  plot_data <- data.frame(time = parsed_dates, value = values)
  time_axis <- list(
    type = "date",
    start = as.character(min(parsed_dates)),
    end = as.character(max(parsed_dates)),
    span_days = as.numeric(max(parsed_dates) - min(parsed_dates))
  )
} else {
  plot_data <- data.frame(time = seq_along(values), value = values)
  time_axis <- list(type = "index", start = 1L, end = length(values))
}

p <- ggplot(plot_data, aes(x = time, y = value, group = 1)) +
  geom_line(color = "steelblue", linewidth = 1) +
  geom_point(alpha = 0.6, color = "steelblue") +
  labs(title = title, x = if (has_dates) "Date" else "Observation", y = "Value")
if (show_trend) {
  p <- p + geom_smooth(method = "lm", formula = y ~ x, se = FALSE, color = "firebrick")
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
# Prepare result
result <- list(
  plot_type = "time_series_plot",
  statistics = list(
    mean = mean(values, na.rm = TRUE),
    sd = sd(values, na.rm = TRUE),
    min = min(values, na.rm = TRUE),
    max = max(values, na.rm = TRUE),
    range = max(values, na.rm = TRUE) - min(values, na.rm = TRUE),
    n_obs = sum(!is.na(values))
  ),
  has_dates = has_dates,
  time_axis = time_axis,
  show_trend = show_trend,
  dimensions = list(width = width, height = height)
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
