# Normality Test Analysis Script for RMCP
# ========================================
#
# This script tests variables for normality using Shapiro-Wilk, Jarque-Bera,
# or Anderson-Darling tests. It includes descriptive statistics and distributional
# properties to help assess normality.

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
test_type <- args$test %||% "shapiro"

values <- data[[variable]]
values <- values[!is.na(values)]
n <- length(values)

if (test_type == "shapiro") {
    # Check Shapiro-Wilk sample size limits
    if (n > 5000) {
        warning("Sample size (", n, ") is large for Shapiro-Wilk test. Consider using Anderson-Darling test for better reliability.")
    }
    if (n < 3) {
        stop("Shapiro-Wilk test requires at least 3 observations")
    }
    
    test_result <- shapiro.test(values)
    result <- list(
        test_name = "Shapiro-Wilk normality test",
        statistic = as.numeric(test_result$statistic),
        p_value = test_result$p.value,
        is_normal = test_result$p.value > 0.05
    )
} else if (test_type == "jarque_bera") {
    if (!requireNamespace("tseries", quietly = TRUE)) {
        stop("Package 'tseries' is required for Jarque-Bera test but not installed")
    }
    library(tseries)
    
    test_result <- jarque.bera.test(values)
    result <- list(
        test_name = "Jarque-Bera normality test",
        statistic = as.numeric(test_result$statistic),
        df = test_result$parameter,
        p_value = test_result$p.value,
        is_normal = test_result$p.value > 0.05
    )
} else if (test_type == "anderson") {
    if (!requireNamespace("nortest", quietly = TRUE)) {
        stop("Package 'nortest' is required for Anderson-Darling test but not installed")
    }
    library(nortest)
    
    test_result <- ad.test(values)
    result <- list(
        test_name = "Anderson-Darling normality test",
        statistic = as.numeric(test_result$statistic),
        p_value = test_result$p.value,
        is_normal = test_result$p.value > 0.05
    )
}

result$variable <- variable
result$n_obs <- n
result$mean <- mean(values)
result$sd <- sd(values)
result$skewness <- (sum((values - mean(values))^3) / n) / (sd(values)^3)
result$excess_kurtosis <- (sum((values - mean(values))^4) / n) / (sd(values)^4) - 3

# Add formatting
result$"_formatting" <- list(
    summary = format_result_table(test_result, paste0(result$test_name, " Results")),
    interpretation = interpret_result(test_result, result$test_name)
)
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
