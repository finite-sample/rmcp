# Formula Validation Script for RMCP
# ===================================
#
# This script validates R formulas against provided data to ensure
# variable existence and identify potential data quality issues.

# Convert data to data frame

# Load required libraries
library(jsonlite)

# Determine script directory for path resolution
script_dir <- if (exists("testthat_testing") && testthat_testing) {
    # Running under testthat - use relative path from test directory
    file.path("..", "..", "R")
} else {
    # Try multiple possible paths for utils.R
    possible_paths <- c(
        file.path("..", "..", "R"),  # Normal relative path
        file.path(getwd(), "rmcp", "r_assets", "R"),  # From project root
        file.path(getwd(), "R"),  # Direct R directory
        "/workspace/rmcp/r_assets/R"  # Docker path
    )
    
    # Try to add script-relative path if possible
    tryCatch({
        script_location <- sys.frame(1)$ofile
        if (!is.null(script_location)) {
            script_based_path <- file.path(dirname(script_location), "..", "..", "R")
            possible_paths <- c(possible_paths, script_based_path)
        }
    }, error = function(e) {
        # sys.frame() not available or no calling frame - continue without it
    })
    
    # Find the first path that contains utils.R
    found_path <- NULL
    for (path in possible_paths) {
        if (file.exists(file.path(path, "utils.R"))) {
            found_path <- path
            break
        }
    }
    
    if (is.null(found_path)) {
        file.path("..", "..", "R")  # Fallback to default
    } else {
        found_path
    }
}

# Load RMCP utilities
utils_path <- file.path(script_dir, "utils.R")
if (file.exists(utils_path)) {
    source(utils_path)
} else {
    stop("Cannot find RMCP utilities at: ", utils_path)
}

# Parse command line arguments
if (!exists("args")) {
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
}


# Validate input
args <- validate_json_input(args, required = c("data"))

# Main script logic
formula_str <- args$formula
data <- as.data.frame(args$data)

# Parse formula
tryCatch({
    parsed_formula <- as.formula(formula_str)
    # Extract variable names
    vars_in_formula <- all.vars(parsed_formula)
    vars_in_data <- names(data)
    
    # Check which variables exist
    missing_vars <- vars_in_formula[!vars_in_formula %in% vars_in_data]
    existing_vars <- vars_in_formula[vars_in_formula %in% vars_in_data]
    
    # Get variable types for existing variables
    var_types <- sapply(data[existing_vars], class)
    
    # Check for potential issues
    warnings <- c()
    
    # Check for missing values
    missing_counts <- sapply(data[existing_vars], function(x) sum(is.na(x)))
    high_missing <- names(missing_counts[missing_counts > 0.1 * nrow(data)])
    if (length(high_missing) > 0) {
        warnings <- c(warnings, paste("High missing values in:", paste(high_missing, collapse=", ")))
    }
    
    # Check for character variables (might need factors)
    char_vars <- names(var_types[var_types == "character"])
    if (length(char_vars) > 0) {
        warnings <- c(warnings, paste("Character variables (consider converting to factors):", paste(char_vars, collapse=", ")))
    }
    
    result <- list(
        is_valid = length(missing_vars) == 0,
        missing_variables = missing_vars,
        existing_variables = existing_vars,
        available_variables = vars_in_data,
        variable_types = as.list(setNames(var_types, names(var_types))),
        warnings = if(length(warnings) == 0) character(0) else warnings,
        formula_parsed = TRUE
    )
}, error = function(e) {
    result <- list(
        is_valid = FALSE,
        error = e$message,
        formula_parsed = FALSE
    )
})
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
