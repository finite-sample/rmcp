# Scatter Plot Visualization Script for RMCP
# ===========================================
#
# This script creates scatter plots with optional grouping and trend lines
# using ggplot2 for publication-quality visualizations.

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
    tryCatch({
        fromJSON(cmd_args[1])
    }, error = function(e) {
        stop("Failed to parse JSON arguments: ", e$message)
    })
}


# Validate input
args <- validate_json_input(args, required = c("data"))

# Main script logic
options(repos = c(CRAN = "https://cloud.r-project.org/"))
library(ggplot2)

# Prepare data and parameters
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

# Create base plot
p <- ggplot(data, aes_string(x = x_var, y = y_var))
if (!is.null(group_var)) {
    p <- p + geom_point(aes_string(color = group_var), alpha = 0.7) +
         geom_smooth(aes_string(color = group_var), method = "lm", se = TRUE)
} else {
    p <- p + geom_point(alpha = 0.7) +
         geom_smooth(method = "lm", se = TRUE, color = "blue")
}
p <- p + labs(title = title, x = x_var, y = y_var) +
     theme_minimal() +
     theme(plot.title = element_text(hjust = 0.5))

# Save to file if path provided
if (!is.null(file_path)) {
    ggsave(file_path, plot = p, width = width/100, height = height/100, dpi = 100)
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
