"""
Data transformation tools for RMCP.
Essential data manipulation and cleaning capabilities.
"""

from typing import Any

from ..core.schemas import table_schema
from ..r_assets.loader import get_r_script
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="lag_lead",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "lags": {"type": "array", "items": {"type": "integer"}},
            "leads": {"type": "array", "items": {"type": "integer"}},
        },
        "required": ["data", "variables"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "Transformed dataset with lag/lead variables",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": ["number", "string", "null"]},
                },
            },
            "variables_created": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names of newly created lag/lead variables",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations in result",
                "minimum": 0,
            },
            "operation": {
                "type": "string",
                "enum": ["lag_lead"],
                "description": "Type of transformation performed",
            },
        },
        "required": ["data", "variables_created", "n_obs", "operation"],
        "additionalProperties": False,
    },
    description="Creates lagged (past values) and lead (future values) variables for time series analysis and panel data. Supports multiple lags/leads simultaneously and handles missing values appropriately. Essential for autoregressive models, studying temporal dependencies, creating predictor variables from time series, or analyzing causality relationships. Use for ARIMA preprocessing, econometric modeling, or feature engineering in time-dependent data.",
)
async def lag_lead(context, params) -> dict[str, Any]:
    """Create lagged and lead variables."""
    await context.info("Creating lag/lead variables")

    r_script = get_r_script("transforms", "lag_lead")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Lag/lead variables created successfully")
        return result
    except Exception as e:
        await context.error("Lag/lead creation failed", error=str(e))
        raise


@tool(
    name="winsorize",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "percentiles": {
                "type": "array",
                "items": {"type": "number", "minimum": 0, "maximum": 1},
                "minItems": 2,
                "maxItems": 2,
                "default": [0.05, 0.95],
                "description": "Lower and upper percentiles for winsorization [lower, upper]",
            },
        },
        "required": ["data", "variables"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "Dataset with winsorized variables",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": ["number", "string", "null"]},
                },
            },
            "outliers_summary": {
                "type": "object",
                "description": "Summary of outliers capped by variable",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "lower_threshold": {"type": "number"},
                        "upper_threshold": {"type": "number"},
                        "n_capped_lower": {"type": "integer", "minimum": 0},
                        "n_capped_upper": {"type": "integer", "minimum": 0},
                        "total_capped": {"type": "integer", "minimum": 0},
                    },
                },
            },
            "percentiles": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Percentile thresholds used for winsorization",
            },
            "variables_winsorized": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables that were winsorized",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations in result",
                "minimum": 0,
            },
        },
        "required": [
            "data",
            "outliers_summary",
            "percentiles",
            "variables_winsorized",
            "n_obs",
        ],
        "additionalProperties": False,
    },
    description="Winsorizes variables by replacing extreme values with specified percentiles to reduce outlier impact while preserving data structure. Sets values below lower percentile to that percentile value and values above upper percentile to that percentile value. More robust than trimming since it retains all observations. Use for outlier treatment in regression analysis, robust statistical modeling, or preparing data for parametric analyzes sensitive to extreme values.",
)
async def winsorize(context, params) -> dict[str, Any]:
    """Winsorize variables to handle outliers."""
    await context.info("Winsorizing variables")

    r_script = get_r_script("transforms", "winsorize")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Variables winsorized successfully")
        return result
    except Exception as e:
        await context.error("Winsorization failed", error=str(e))
        raise


@tool(
    name="difference",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "order": {"type": "integer", "minimum": 1, "maximum": 3, "default": 1},
            "log_transform": {"type": "boolean", "default": False},
        },
        "required": ["data", "variables"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "Dataset with differenced variables",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": ["number", "string", "null"]},
                },
            },
            "variables_differenced": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Original variables that were differenced",
            },
            "difference_order": {
                "type": "integer",
                "description": "Order of differencing applied",
                "minimum": 1,
                "maximum": 3,
            },
            "log_transformed": {
                "type": "boolean",
                "description": "Whether log transformation was applied before differencing",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations in result",
                "minimum": 0,
            },
        },
        "required": [
            "data",
            "variables_differenced",
            "difference_order",
            "log_transformed",
            "n_obs",
        ],
        "additionalProperties": False,
    },
    description="Computes first differences, seasonal differences, or higher-order differences to transform non-stationary time series into stationary ones. Essential preprocessing step for ARIMA modeling and many econometric analyzes. Returns differenced series and handles missing values created by differencing. Use to remove trends, achieve stationarity for time series models, or analyze period-to-period changes in economic and financial data.",
)
async def difference(context, params) -> dict[str, Any]:
    """Compute differences of variables."""
    await context.info("Computing variable differences")

    r_script = get_r_script("transforms", "difference")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Variable differences computed successfully")
        return result
    except Exception as e:
        await context.error("Differencing failed", error=str(e))
        raise


@tool(
    name="standardize",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "method": {
                "type": "string",
                "enum": ["z_score", "min_max", "robust"],
                "default": "z_score",
            },
        },
        "required": ["data", "variables"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "Dataset with standardized variables",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": ["number", "string", "null"]},
                },
            },
            "scaling_method": {
                "type": "string",
                "enum": ["z_score", "min_max", "robust"],
                "description": "Standardization method used",
            },
            "scaling_info": {
                "type": "object",
                "description": "Scaling parameters for each variable",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": {"type": "number"},
                },
            },
            "variables_scaled": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables that were standardized",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations in result",
                "minimum": 0,
            },
        },
        "required": [
            "data",
            "scaling_method",
            "scaling_info",
            "variables_scaled",
            "n_obs",
        ],
        "additionalProperties": False,
    },
    description="Standardizes variables using multiple scaling methods: z-score normalization (mean=0, sd=1), min-max scaling (range 0-1), or robust scaling (median=0, MAD=1). Essential for machine learning algorithms, principal component analysis, or when combining variables with different units. Handles missing values and provides scaling parameters for inverse transformation. Use before clustering, neural networks, or any analysis requiring comparable variable scales.",
)
async def standardize(context, params) -> dict[str, Any]:
    """Standardize variables."""
    await context.info("Standardizing variables")

    r_script = get_r_script("transforms", "standardize")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Variables standardized successfully")
        return result
    except Exception as e:
        await context.error("Standardization failed", error=str(e))
        raise
