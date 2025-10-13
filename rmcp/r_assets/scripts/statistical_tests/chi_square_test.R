# Chi-Square Test Analysis Script for RMCP
# ========================================
#
# This script performs chi-square tests for independence and goodness of fit.
# It supports testing relationships between categorical variables and comparing
# observed frequencies to expected distributions.

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
x_var <- args$x
y_var <- args$y
test_type <- args$test_type %||% "independence"
expected <- args$expected

if (test_type == "independence") {
    if (is.null(x_var) || is.null(y_var)) {
        stop("Both x and y variables required for independence test")
    }
    
    # Create contingency table
    cont_table <- table(data[[x_var]], data[[y_var]])
    test_result <- chisq.test(cont_table)
    
    result <- list(
        test_type = "Chi-square test of independence",
        contingency_table = as.matrix(cont_table),
        statistic = as.numeric(test_result$statistic),
        df = test_result$parameter,
        p_value = test_result$p.value,
        expected_frequencies = as.matrix(test_result$expected),
        residuals = as.matrix(test_result$residuals),
        x_variable = x_var,
        y_variable = y_var,
        cramers_v = sqrt(test_result$statistic / (sum(cont_table) * (min(dim(cont_table)) - 1))),

        # Special non-validated field for formatting
        "_formatting" = list(
            summary = format_result_table(test_result, "Chi-Square Test"),
            interpretation = interpret_result(test_result, "Chi-square test")
        )
    )
} else {
    # Goodness of fit test
    if (is.null(x_var)) {
        stop("x variable required for goodness of fit test")
    }
    
    observed <- table(data[[x_var]])
    
    if (!is.null(expected)) {
        # Validate expected probabilities
        if (length(expected) != length(observed)) {
            stop(paste("Expected probabilities length (", length(expected),
                      ") must match number of categories (", length(observed), ")"))
        }
        if (any(expected < 0)) {
            stop("Expected probabilities must be non-negative")
        }
        if (sum(expected) == 0) {
            stop("Expected probabilities cannot all be zero")
        }
        
        # Normalize to probabilities (sum to 1)
        p <- expected / sum(expected)
        names(p) <- names(observed)
        test_result <- chisq.test(observed, p = p)
        
        # Warn about low expected counts
        expected_counts <- test_result$expected
        low_expected <- sum(expected_counts < 5)
        if (low_expected > 0) {
            warning(paste(low_expected, "cell(s) have expected counts < 5. Results may be unreliable."))
        }
    } else {
        test_result <- chisq.test(observed)
    }
    
    result <- list(
        test_type = "Chi-square goodness of fit test",
        observed_frequencies = as.numeric(observed),
        expected_frequencies = as.numeric(test_result$expected),
        statistic = as.numeric(test_result$statistic),
        df = test_result$parameter,
        p_value = test_result$p.value,
        residuals = as.numeric(test_result$residuals),
        categories = names(observed),

        # Special non-validated field for formatting
        "_formatting" = list(
            summary = format_result_table(test_result, "Chi-Square Goodness of Fit"),
            interpretation = interpret_result(test_result, "Chi-square test")
        )
    )
}
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
