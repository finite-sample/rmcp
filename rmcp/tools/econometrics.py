"""
Econometric analysis tools for RMCP.
Advanced econometric modeling for panel data, instrumental variables, etc.
"""

from typing import Any

from ..core.schemas import formula_schema, table_schema
from ..r_assets.loader import get_r_script
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="panel_regression",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": formula_schema(),
            "id_variable": {"type": "string"},
            "time_variable": {"type": "string"},
            "model": {
                "type": "string",
                "enum": ["pooling", "within", "between", "random"],
                "default": "within",
            },
            "robust": {"type": "boolean", "default": True},
        },
        "required": ["data", "formula", "id_variable", "time_variable"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "coefficients": {
                "type": "object",
                "description": "Estimated coefficients",
                "additionalProperties": {"type": "number"},
            },
            "std_errors": {
                "type": "object",
                "description": "Standard errors of coefficients",
                "additionalProperties": {"type": "number"},
            },
            "t_values": {
                "type": "object",
                "description": "t-statistics for coefficients",
                "additionalProperties": {"type": "number"},
            },
            "p_values": {
                "type": "object",
                "description": "P-values for coefficient significance tests",
                "additionalProperties": {"type": "number"},
            },
            "r_squared": {
                "type": "number",
                "description": "R-squared (overall fit)",
                "minimum": 0,
                "maximum": 1,
            },
            "adj_r_squared": {
                "type": "number",
                "description": "Adjusted R-squared",
                "maximum": 1,
            },
            "model_type": {
                "type": "string",
                "enum": ["pooling", "within", "between", "random"],
                "description": "Type of panel model estimated",
            },
            "robust_se": {
                "type": "boolean",
                "description": "Whether robust standard errors were used",
            },
            "n_obs": {
                "type": "integer",
                "description": "Total number of observations",
                "minimum": 1,
            },
            "n_groups": {
                "type": "integer",
                "description": "Number of cross-sectional units",
                "minimum": 1,
            },
            "time_periods": {
                "type": "integer",
                "description": "Number of time periods",
                "minimum": 1,
            },
            "formula": {"type": "string", "description": "Model formula used"},
            "id_variable": {
                "type": "string",
                "description": "Cross-sectional identifier variable",
            },
            "time_variable": {
                "type": "string",
                "description": "Time identifier variable",
            },
        },
        "required": [
            "coefficients",
            "std_errors",
            "t_values",
            "p_values",
            "r_squared",
            "adj_r_squared",
            "model_type",
            "robust_se",
            "n_obs",
            "n_groups",
            "time_periods",
            "formula",
            "id_variable",
            "time_variable",
        ],
        "additionalProperties": False,
    },
    description="Performs panel data regression analysis with fixed effects, random effects, or between/pooling estimators for longitudinal data. Handles unbalanced panels, robust standard errors, and provides Hausman tests for model selection. Essential for analyzing repeated observations on same units over time. Use for causal inference, policy evaluation, individual heterogeneity control, or any analysis with cross-sectional time series data.",
)
async def panel_regression(context, params) -> dict[str, Any]:
    """Perform panel data regression."""
    await context.info("Fitting panel data regression")

    r_script = get_r_script("econometrics", "panel_regression")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Panel regression completed successfully")
        return result
    except Exception as e:
        await context.error("Panel regression failed", error=str(e))
        raise


@tool(
    name="instrumental_variables",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": {
                "type": "string",
                "description": "Format: 'y ~ x1 + x2 | z1 + z2' where | separates instruments",
            },
            "robust": {"type": "boolean", "default": True},
        },
        "required": ["data", "formula"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "coefficients": {
                "type": "object",
                "description": "2SLS coefficient estimates",
                "additionalProperties": {"type": "number"},
            },
            "std_errors": {
                "type": "object",
                "description": "Standard errors of coefficients",
                "additionalProperties": {"type": "number"},
            },
            "t_values": {
                "type": "object",
                "description": "t-statistics for coefficients",
                "additionalProperties": {"type": "number"},
            },
            "p_values": {
                "type": "object",
                "description": "P-values for coefficient significance tests",
                "additionalProperties": {"type": "number"},
            },
            "r_squared": {
                "type": "number",
                "description": "R-squared value",
                "maximum": 1,
            },
            "adj_r_squared": {
                "type": "number",
                "description": "Adjusted R-squared value",
                "maximum": 1,
            },
            "weak_instruments": {
                "type": "object",
                "properties": {
                    "statistic": {
                        "type": "number",
                        "description": "Weak instruments test statistic",
                    },
                    "p_value": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "P-value for weak instruments test",
                    },
                },
                "description": "Test for weak instruments",
            },
            "wu_hausman": {
                "type": "object",
                "properties": {
                    "statistic": {
                        "type": "number",
                        "description": "Wu-Hausman test statistic",
                    },
                    "p_value": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "P-value for Wu-Hausman test",
                    },
                },
                "description": "Test for endogeneity",
            },
            "sargan": {
                "type": "object",
                "properties": {
                    "statistic": {
                        "type": "number",
                        "description": "Sargan test statistic",
                    },
                    "p_value": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "P-value for Sargan test",
                    },
                },
                "description": "Test for overidentifying restrictions",
            },
            "robust_se": {
                "type": "boolean",
                "description": "Whether robust standard errors were used",
            },
            "formula": {"type": "string", "description": "IV regression formula used"},
            "n_obs": {
                "type": "integer",
                "description": "Number of observations",
                "minimum": 1,
            },
        },
        "required": [
            "coefficients",
            "std_errors",
            "t_values",
            "p_values",
            "r_squared",
            "adj_r_squared",
            "weak_instruments",
            "wu_hausman",
            "sargan",
            "robust_se",
            "formula",
            "n_obs",
        ],
        "additionalProperties": False,
    },
    description="Performs Two-Stage Least Squares (2SLS) instrumental variables regression to address endogeneity bias when explanatory variables are correlated with error terms. Provides first-stage statistics, weak instrument tests, and overidentification tests. Critical for causal inference when randomized experiments are not possible. Use for addressing simultaneity, measurement error, omitted variable bias, or establishing causal relationships in observational data.",
)
async def instrumental_variables(context, params) -> dict[str, Any]:
    """Perform instrumental variables regression."""
    await context.info("Fitting instrumental variables model")

    r_script = get_r_script("econometrics", "instrumental_variables")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Instrumental variables model fitted successfully")
        return result
    except Exception as e:
        await context.error("Instrumental variables fitting failed", error=str(e))
        raise


@tool(
    name="var_model",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "lags": {"type": "integer", "minimum": 1, "maximum": 10, "default": 2},
            "type": {
                "type": "string",
                "enum": ["const", "trend", "both", "none"],
                "default": "const",
            },
        },
        "required": ["data", "variables"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "equations": {
                "type": "object",
                "description": "Results for each equation in the VAR system",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "coefficients": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                            "description": "Coefficient estimates",
                        },
                        "std_errors": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                            "description": "Standard errors",
                        },
                        "t_values": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                            "description": "t-statistics",
                        },
                        "p_values": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                            "description": "P-values",
                        },
                        "r_squared": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "R-squared for this equation",
                        },
                        "adj_r_squared": {
                            "type": "number",
                            "maximum": 1,
                            "description": "Adjusted R-squared for this equation",
                        },
                    },
                },
            },
            "variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables included in the VAR system",
            },
            "lag_order": {
                "type": "integer",
                "description": "Number of lags in the VAR model",
                "minimum": 1,
                "maximum": 10,
            },
            "var_type": {
                "type": "string",
                "enum": ["const", "trend", "both", "none"],
                "description": "Type of deterministic terms included",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations used",
                "minimum": 1,
            },
            "n_variables": {
                "type": "integer",
                "description": "Number of variables in the system",
                "minimum": 2,
            },
            "loglik": {"type": "number", "description": "Log-likelihood value"},
            "aic": {"type": "number", "description": "Akaike Information Criterion"},
            "bic": {"type": "number", "description": "Bayesian Information Criterion"},
            "residual_covariance": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "number"}},
                "description": "Residual covariance matrix",
            },
        },
        "required": [
            "equations",
            "variables",
            "lag_order",
            "var_type",
            "n_obs",
            "n_variables",
            "loglik",
            "aic",
            "bic",
            "residual_covariance",
        ],
        "additionalProperties": False,
    },
    description="Estimates Vector Autoregression (VAR) models for analyzing dynamic relationships among multiple time series variables. Each variable is modeled as linear function of its own lags and lags of all other variables. Provides impulse response functions, variance decomposition, and Granger causality tests. Use for macroeconomic modeling, forecasting multiple related time series, understanding dynamic interdependencies, or analyzing shock transmission between variables.",
)
async def var_model(context, params) -> dict[str, Any]:
    """Fit Vector Autoregression model."""
    await context.info("Fitting VAR model")

    r_script = get_r_script("econometrics", "var_model")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("VAR model fitted successfully")
        return result
    except Exception as e:
        await context.error("VAR model fitting failed", error=str(e))
        raise
