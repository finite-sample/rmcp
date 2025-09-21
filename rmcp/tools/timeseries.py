"""
Time series analysis tools for RMCP.

Comprehensive time series modeling and forecasting capabilities.
"""

from typing import Any

from ..core.schemas import table_schema
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="arima_model",
    input_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "values": {"type": "array", "items": {"type": "number"}},
                    "dates": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["values"],
            },
            "order": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 3,
                "maxItems": 3,
                "description": "ARIMA order (p, d, q)",
            },
            "seasonal": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 4,
                "maxItems": 4,
                "description": "Seasonal ARIMA order (P, D, Q, s)",
            },
            "forecast_periods": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 12,
            },
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "model_type": {
                "type": "string",
                "enum": ["ARIMA"],
                "description": "Type of time series model",
            },
            "order": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "ARIMA order (p, d, q) and seasonal order if applicable",
            },
            "coefficients": {
                "type": "object",
                "description": "Model coefficients",
                "additionalProperties": {"type": "number"},
            },
            "aic": {"type": "number", "description": "Akaike Information Criterion"},
            "bic": {"type": "number", "description": "Bayesian Information Criterion"},
            "loglik": {"type": "number", "description": "Log-likelihood value"},
            "sigma2": {
                "type": "number",
                "description": "Estimated innovation variance",
                "minimum": 0,
            },
            "fitted_values": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Fitted values from the model",
            },
            "residuals": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Model residuals",
            },
            "forecasts": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Point forecasts",
            },
            "forecast_lower": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Lower bounds of 95% prediction intervals",
            },
            "forecast_upper": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Upper bounds of 95% prediction intervals",
            },
            "accuracy": {
                "type": "object",
                "description": "Model accuracy metrics",
                "additionalProperties": {"type": "number"},
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations in training data",
                "minimum": 1,
            },
        },
        "required": [
            "model_type",
            "order",
            "aic",
            "bic",
            "loglik",
            "sigma2",
            "fitted_values",
            "residuals",
            "forecasts",
            "forecast_lower",
            "forecast_upper",
            "accuracy",
            "n_obs",
        ],
        "additionalProperties": False,
    },
    description="Fit ARIMA time series model with forecasting",
)
async def arima_model(context, params) -> dict[str, Any]:
    """Fit ARIMA model and generate forecasts."""

    await context.info("Fitting ARIMA time series model")

    r_script = """
    # Install required packages
    library(forecast)
    
    # Prepare data
    values <- args$data$values
    
    # Convert to time series
    if (!is.null(args$data$dates)) {
        dates <- as.Date(args$data$dates)
        ts_data <- ts(values, frequency = 12)  # Assume monthly by default
    } else {
        ts_data <- ts(values, frequency = 12)
    }
    
    # Fit ARIMA model
    if (!is.null(args$order)) {
        if (!is.null(args$seasonal)) {
            model <- Arima(ts_data, order = args$order, seasonal = args$seasonal)
        } else {
            model <- Arima(ts_data, order = args$order)
        }
    } else {
        # Auto ARIMA
        model <- auto.arima(ts_data)
    }
    
    # Generate forecasts
    forecast_periods <- args$forecast_periods %||% 12
    forecasts <- forecast(model, h = forecast_periods)
    
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
        n_obs = length(values)
    )
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "ARIMA model fitted successfully",
            aic=result.get("aic"),
            n_obs=result.get("n_obs"),
        )
        return result

    except Exception as e:
        await context.error("ARIMA model fitting failed", error=str(e))
        raise


@tool(
    name="decompose_timeseries",
    input_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "values": {"type": "array", "items": {"type": "number"}},
                    "dates": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["values"],
            },
            "frequency": {"type": "integer", "minimum": 1, "default": 12},
            "type": {
                "type": "string",
                "enum": ["additive", "multiplicative"],
                "default": "additive",
            },
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "original": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Original time series values",
            },
            "trend": {
                "type": "array",
                "items": {"type": ["number", "null"]},
                "description": "Trend component (may contain null values at ends)",
            },
            "seasonal": {
                "type": "array",
                "items": {"type": ["number", "null"]},
                "description": "Seasonal component",
            },
            "remainder": {
                "type": "array",
                "items": {"type": ["number", "null"]},
                "description": "Remainder/irregular component",
            },
            "type": {
                "type": "string",
                "enum": ["additive", "multiplicative"],
                "description": "Type of decomposition performed",
            },
            "frequency": {
                "type": "integer",
                "description": "Seasonal frequency used",
                "minimum": 1,
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations in time series",
                "minimum": 1,
            },
        },
        "required": [
            "original",
            "trend",
            "seasonal",
            "remainder",
            "type",
            "frequency",
            "n_obs",
        ],
        "additionalProperties": False,
    },
    description="Decompose time series into trend, seasonal, and remainder components",
)
async def decompose_timeseries(context, params) -> dict[str, Any]:
    """Decompose time series into components."""

    await context.info("Decomposing time series")

    r_script = """
    
    values <- args$data$values
    frequency <- args$frequency %||% 12
    decomp_type <- args$type %||% "additive"
    
    # Create time series
    ts_data <- ts(values, frequency = frequency)
    
    # Decompose
    if (decomp_type == "multiplicative") {
        decomp <- decompose(ts_data, type = "multiplicative")
    } else {
        decomp <- decompose(ts_data, type = "additive")
    }
    
    result <- list(
        original = as.numeric(decomp$x),
        trend = as.numeric(decomp$trend),
        seasonal = as.numeric(decomp$seasonal),  
        remainder = as.numeric(decomp$random),
        type = decomp_type,
        frequency = frequency,
        n_obs = length(values)
    )
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Time series decomposed successfully")
        return result

    except Exception as e:
        await context.error("Time series decomposition failed", error=str(e))
        raise


@tool(
    name="stationarity_test",
    input_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "values": {"type": "array", "items": {"type": "number"}}
                },
                "required": ["values"],
            },
            "test": {"type": "string", "enum": ["adf", "kpss", "pp"], "default": "adf"},
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "test_name": {
                "type": "string",
                "description": "Full name of the stationarity test",
                "enum": ["Augmented Dickey-Fuller", "KPSS", "Phillips-Perron"],
            },
            "test_type": {
                "type": "string",
                "description": "Short test identifier",
                "enum": ["adf", "kpss", "pp"],
            },
            "statistic": {"type": "number", "description": "Test statistic value"},
            "p_value": {
                "type": "number",
                "description": "P-value of the test",
                "minimum": 0,
                "maximum": 1,
            },
            "critical_values": {
                "type": "object",
                "description": "Critical values at different significance levels",
                "additionalProperties": {"type": "number"},
            },
            "alternative": {"type": "string", "description": "Alternative hypothesis"},
            "is_stationary": {
                "type": "boolean",
                "description": "Whether time series appears to be stationary",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations in time series",
                "minimum": 1,
            },
        },
        "required": [
            "test_name",
            "test_type",
            "statistic",
            "p_value",
            "critical_values",
            "alternative",
            "is_stationary",
            "n_obs",
        ],
        "additionalProperties": False,
    },
    description="Test time series for stationarity (ADF, KPSS, Phillips-Perron)",
)
async def stationarity_test(context, params) -> dict[str, Any]:
    """Test time series stationarity."""

    await context.info("Testing time series stationarity")

    r_script = """
    library(tseries)
    
    values <- args$data$values
    test_type <- args$test %||% "adf"
    
    ts_data <- ts(values)
    
    if (test_type == "adf") {
        test_result <- adf.test(ts_data)
        test_name <- "Augmented Dickey-Fuller"
    } else if (test_type == "kpss") {
        test_result <- kpss.test(ts_data) 
        test_name <- "KPSS"
    } else if (test_type == "pp") {
        test_result <- pp.test(ts_data)
        test_name <- "Phillips-Perron"
    }
    
    result <- list(
        test_name = test_name,
        test_type = test_type,
        statistic = as.numeric(test_result$statistic),
        p_value = test_result$p.value,
        critical_values = as.list(test_result$critical),
        alternative = test_result$alternative,
        is_stationary = if (test_type == "kpss") test_result$p.value > 0.05 else test_result$p.value < 0.05,
        n_obs = length(values)
    )
    """

    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "Stationarity test completed",
            test=result.get("test_name"),
            p_value=result.get("p_value"),
        )
        return result

    except Exception as e:
        await context.error("Stationarity test failed", error=str(e))
        raise
