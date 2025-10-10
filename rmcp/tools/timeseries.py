"""
Time series analysis tools for RMCP.
Comprehensive time series modeling and forecasting capabilities.
"""

from typing import Any

from ..r_assets.loader import get_r_script
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
    description="Fits ARIMA (AutoRegressive Integrated Moving Average) models for time series forecasting and analysis. Automatically selects optimal model parameters or uses specified orders, generates point forecasts with confidence intervals, and provides model diagnostics including AIC/BIC. Use for forecasting future values, understanding temporal patterns, or modeling autocorrelated data. Handles both non-seasonal and seasonal ARIMA models with integrated differencing for non-stationary series.",
)
async def arima_model(context, params) -> dict[str, Any]:
    """Fit ARIMA model and generate forecasts."""
    await context.info("Fitting ARIMA time series model")

    r_script = get_r_script("timeseries", "arima_model")
    try:
        result = await execute_r_script_async(r_script, params, context)
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
    description="Decomposes time series into constituent components: trend (long-term movement), seasonal (repeating patterns), and remainder (irregular fluctuations). Supports both additive and multiplicative decomposition methods. Use to understand underlying patterns, identify seasonal effects, detect structural changes, or prepare data for forecasting. Essential for exploratory time series analysis and identifying appropriate modeling approaches.",
)
async def decompose_timeseries(context, params) -> dict[str, Any]:
    """Decompose time series into components."""
    await context.info("Decomposing time series")

    r_script = get_r_script("timeseries", "decompose_timeseries")
    try:
        result = await execute_r_script_async(r_script, params, context)
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
    description="Tests time series for stationarity using Augmented Dickey-Fuller (ADF), Kwiatkowski-Phillips-Schmidt-Shin (KPSS), or Phillips-Perron tests. Stationarity is required for many time series models like ARIMA. Returns test statistics, p-values, critical values, and clear interpretation. Use before time series modeling to determine if differencing is needed, or to verify model assumptions. ADF tests for unit roots, KPSS tests trend stationarity.",
)
async def stationarity_test(context, params) -> dict[str, Any]:
    """Test time series stationarity."""
    await context.info("Testing time series stationarity")

    r_script = get_r_script("timeseries", "stationarity_test")
    try:
        result = await execute_r_script_async(r_script, params, context)
        await context.info(
            "Stationarity test completed",
            test=result.get("test_name"),
            p_value=result.get("p_value"),
        )
        return result
    except Exception as e:
        await context.error("Stationarity test failed", error=str(e))
        raise
