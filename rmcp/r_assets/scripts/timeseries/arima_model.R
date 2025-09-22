# ARIMA Time Series Modeling Script for RMCP
# ===========================================
#
# This script fits ARIMA models to time series data with automatic or manual
# order selection and generates forecasts with prediction intervals.

# Install required packages
library(forecast)

# Prepare data
rmcp_progress("Preparing time series data")
values <- args$data$values

# Convert to time series
if (!is.null(args$data$dates)) {
    dates <- as.Date(args$data$dates)
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
    accuracy = accuracy(model),
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