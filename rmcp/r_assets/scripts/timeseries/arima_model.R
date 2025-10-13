# ARIMA Time Series Modeling Script for RMCP
# ===========================================
#
# This script fits ARIMA models to time series data with automatic or manual
# order selection and generates forecasts with prediction intervals.

# Install required packages

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
library(forecast)

# Prepare data
rmcp_progress("Preparing time series data")

# Convert to time series
    ts_data <- ts(values, frequency = 12)  # Assume monthly by default
} else {
    ts_data <- ts(values, frequency = 12)
}

# Fit ARIMA model with progress reporting
rmcp_progress("Fitting ARIMA model", 20, 100)
if (!is.null(args$order)) {
    if (!is.null(args$seasonal)) {
        model <- Arima(ts_data, order = args$order, seasonal = args$seasonal)
    } else {
        model <- Arima(ts_data, order = args$order)
    }
} else {
    # Auto ARIMA (can be slow for large datasets)
    rmcp_progress("Running automatic ARIMA model selection", 30, 100)
    model <- auto.arima(ts_data)
}
rmcp_progress("ARIMA model fitted successfully", 70, 100)

# Generate forecasts
rmcp_progress("Generating forecasts", 80, 100)
forecast_periods <- args$forecast_periods %||% 12
forecasts <- forecast(model, h = forecast_periods)
rmcp_progress("Extracting model results", 95, 100)

# Extract results
result <- list(
    model_type = "ARIMA",
    order = arimaorder(model),
    coefficients = as.list(coef(model)),
    aic = AIC(model),
    bic = BIC(model),
    loglik = logLik(model)[1],
    sigma2 = model$sigma2,
    fitted_values = as.numeric(fitted(model)),
    residuals = as.numeric(residuals(model)),
    forecasts = as.numeric(forecasts$mean),
    forecast_lower = as.numeric(forecasts$lower[,2]),  # 95% CI
    forecast_upper = as.numeric(forecasts$upper[,2]),
    accuracy = Filter(function(x) !is.na(x) && !is.null(x), as.list(as.data.frame(accuracy(model))[1,])),  # Convert to named list, remove NAs
    n_obs = length(values),

    # Special non-validated field for formatting
    "_formatting" = list(
        summary = tryCatch({
            # Try to tidy the ARIMA model
            tidy_model <- broom::tidy(model)
            as.character(knitr::kable(
                tidy_model, format = "markdown", digits = 4
            ))
        }, error = function(e) {
            # Fallback: create summary table
            model_summary <- data.frame(
                Model = "ARIMA",
                AIC = AIC(model),
                BIC = BIC(model),
                Observations = length(values)
            )
            as.character(knitr::kable(
                model_summary, format = "markdown", digits = 4
            ))
        }),
        interpretation = paste0("ARIMA model fitted with AIC = ", round(AIC(model), 2),
                              ". Forecasted ", forecast_periods, " periods ahead.")
    )
)
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
