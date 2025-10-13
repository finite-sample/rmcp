# T-Test Analysis Script for RMCP
# ===============================
#
# This script performs t-test analysis including one-sample, two-sample, and paired t-tests.
# It handles different types of t-tests based on the provided parameters and returns
# comprehensive test statistics and confidence intervals.

# Prepare data and parameters

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
variable <- args$variable
group <- args$group
mu <- args$mu %||% 0
alternative <- args$alternative %||% "two.sided"
paired <- args$paired %||% FALSE
var_equal <- args$var_equal %||% FALSE

if (is.null(group)) {
    # One-sample t-test
    test_result <- t.test(data[[variable]], mu = mu, alternative = alternative)
    test_type <- "One-sample t-test"
    
    # Clean data
    values <- data[[variable]][!is.na(data[[variable]])]
    
    result <- list(
        test_type = test_type,
        statistic = as.numeric(test_result$statistic),
        df = test_result$parameter,
        p_value = test_result$p.value,
        confidence_interval = list(
            lower = as.numeric(test_result$conf.int[1]),
            upper = as.numeric(test_result$conf.int[2]),
            level = attr(test_result$conf.int, "conf.level") %||% 0.95
        ),
        mean = as.numeric(test_result$estimate),
        null_value = mu,
        alternative = alternative,
        n_obs = length(values),

        # Special non-validated field for formatting
        "_formatting" = list(
            summary = format_result_table(test_result, "T-Test Results"),
            interpretation = interpret_result(test_result, "T-test")
        )
    )
} else {
    # Two-sample t-test
    group_values <- data[[group]]
    
    # Sort groups consistently and handle NA values
    unique_groups <- sort(unique(stats::na.omit(group_values)))
    if (length(unique_groups) != 2) {
        stop("Group variable must have exactly 2 levels")
    }
    
    # Extract and clean data for each group
    x <- data[[variable]][group_values == unique_groups[1]]
    y <- data[[variable]][group_values == unique_groups[2]]
    x <- x[!is.na(x)]
    y <- y[!is.na(y)]
    
    test_result <- t.test(x, y, alternative = alternative, paired = paired, var.equal = var_equal)
    test_type <- if (paired) "Paired t-test" else if (var_equal) "Two-sample t-test (equal variances)" else "Welch's t-test"
    
    result <- list(
        test_type = test_type,
        statistic = as.numeric(test_result$statistic),
        df = test_result$parameter,
        p_value = test_result$p.value,
        confidence_interval = list(
            lower = as.numeric(test_result$conf.int[1]),
            upper = as.numeric(test_result$conf.int[2]),
            level = attr(test_result$conf.int, "conf.level") %||% 0.95
        ),
        mean_x = as.numeric(test_result$estimate[1]),
        mean_y = as.numeric(test_result$estimate[2]),
        mean_difference = as.numeric(test_result$estimate[1] - test_result$estimate[2]),
        groups = unique_groups,
        alternative = alternative,
        paired = paired,
        var_equal = var_equal,
        n_obs_x = length(x),
        n_obs_y = length(y),

        # Special non-validated field for formatting
        "_formatting" = list(
            summary = format_result_table(test_result, "T-Test Results"),
            interpretation = interpret_result(test_result, "T-test")
        )
    )
}
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
