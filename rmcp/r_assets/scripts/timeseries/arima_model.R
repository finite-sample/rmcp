# ARIMA Time Series Modeling Script for RMCP
# ===========================================
#
# This script fits ARIMA models to time series data with automatic or manual
# order selection and generates forecasts with prediction intervals.

# Load required libraries
library(forecast)
library(broom)
library(knitr)

# Prepare data
rmcp_progress("Preparing time series data")

# Extract data - handle both direct values and data structure
if ("values" %in% names(args$data)) {
  # Data comes from Python schema with data.values structure
  values <- args$data$values
} else if ("value_col" %in% names(args)) {
  # Legacy column-based extraction
  value_col <- args$value_col %||% "value"
  if (value_col %in% names(data)) {
    values <- data[[value_col]]
  } else {
    # Find first numeric column
    numeric_cols <- names(data)[sapply(data, is.numeric)]
    if (length(numeric_cols) > 0) {
      values <- data[[numeric_cols[1]]]
      warning(paste("Column", value_col, "not found, using", numeric_cols[1]))
    } else {
      stop("No numeric columns found for time series analysis")
    }
  }
} else {
  # Try to find values in data directly
  numeric_cols <- names(data)[sapply(data, is.numeric)]
  if (length(numeric_cols) > 0) {
    values <- data[[numeric_cols[1]]]
  } else {
    stop("No numeric data found for time series analysis")
  }
}
# Convert to time series
frequency <- args$frequency %||% 12 # Default to monthly data
ts_data <- ts(values, frequency = frequency)
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
  forecast_lower = as.numeric(forecasts$lower[, 2]), # 95% CI
  forecast_upper = as.numeric(forecasts$upper[, 2]),
  accuracy = Filter(function(x) !is.na(x) && !is.null(x), as.list(as.data.frame(accuracy(model))[1, ])), # Convert to named list, remove NAs
  n_obs = length(values),
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Try to tidy the ARIMA model
        tidy_model <- broom::tidy(model)
        paste(as.character(knitr::kable(
          tidy_model,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        # Fallback: create summary table
        model_summary <- data.frame(
          Model = "ARIMA",
          AIC = AIC(model),
          BIC = BIC(model),
          Observations = length(values)
        )
        paste(as.character(knitr::kable(
          model_summary,
          format = "markdown", digits = 4
        )), collapse = "\n")
      }
    ),
    interpretation = paste0(
      "ARIMA model fitted with AIC = ", round(AIC(model), 2),
      ". Forecasted ", forecast_periods, " periods ahead."
    )
  )
)
