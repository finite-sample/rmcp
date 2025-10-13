# Vector Autoregression (VAR) Model Script for RMCP
# ===================================================
#
# This script fits Vector Autoregression models for multivariate time series
# analysis with support for different lag orders and deterministic terms.


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
library(vars)

# Prepare data and parameters
variables <- args$variables
lag_order <- args$lags %||% 2
var_type <- args$type %||% "const"

# Select variables for VAR
var_data <- data[, variables, drop = FALSE]

# Remove missing values
var_data <- na.omit(var_data)

# Fit VAR model
var_model <- VAR(var_data, p = lag_order, type = var_type)

# Extract coefficients for each equation
equations <- list()
for (var in variables) {
    eq_summary <- summary(var_model)$varresult[[var]]
    equations[[var]] <- list(
        coefficients = as.list(coef(eq_summary)),
        std_errors = as.list(eq_summary$coefficients[, "Std. Error"]),
        t_values = as.list(eq_summary$coefficients[, "t value"]),
        p_values = as.list(eq_summary$coefficients[, "Pr(>|t|)"]),
        r_squared = eq_summary$r.squared,
        adj_r_squared = eq_summary$adj.r.squared
    )
}

# Model diagnostics
var_summary <- summary(var_model)

result <- list(
    equations = equations,
    variables = variables,
    lag_order = lag_order,
    var_type = var_type,
    n_obs = nobs(var_model),
    n_variables = length(variables),
    loglik = logLik(var_model)[1],
    aic = AIC(var_model),
    bic = BIC(var_model),
    residual_covariance = as.matrix(var_summary$covres),

    # Special non-validated field for formatting
    "_formatting" = list(
        summary = tryCatch({
            # Create VAR summary table
            var_summary_df <- data.frame(
                Model = "VAR",
                Variables = length(variables),
                Lags = lag_order,
                Observations = nobs(var_model),
                AIC = round(AIC(var_model), 2),
                BIC = round(BIC(var_model), 2)
            )
            as.character(knitr::kable(
                var_summary_df, format = "markdown", digits = 4
            ))
        }, error = function(e) {
            "VAR model fitted successfully"
        }),
        interpretation = paste0("VAR(", lag_order, ") model with ", length(variables),
                              " variables and ", nobs(var_model), " observations.")
    )
)
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
