"""
Regression Analysis Tools for RMCP MCP Server.
This module provides comprehensive regression modeling capabilities including:
- Linear regression with diagnostics
- Logistic regression for binary outcomes
- Correlation analysis with significance testing
- Comprehensive model validation and statistics
All tools support missing value handling, weighted observations, and return
detailed statistical outputs suitable for research and business analysis.
Example Usage:
    >>> # Linear regression on sales data
    >>> data = {"sales": [100, 120, 140], "advertising": [10, 15, 20]}
    >>> result = await linear_model(context, {
    ...     "data": data,
    ...     "formula": "sales ~ advertising"
    ... })
    >>> print(f"R-squared: {result['r_squared']}")
"""

from typing import Any

from ..core.schemas import formula_schema, table_schema
from ..r_assets.loader import get_r_script
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="linear_model",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(required_columns=None),
            "formula": formula_schema(),
            "weights": {"type": "array", "items": {"type": "number"}},
            "na_action": {
                "type": "string",
                "enum": ["na.omit", "na.exclude", "na.fail"],
            },
        },
        "required": ["data", "formula"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "coefficients": {
                "type": "object",
                "description": "Regression coefficients by variable name",
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
                "description": "R-squared (coefficient of determination)",
                "minimum": 0,
                "maximum": 1,
            },
            "adj_r_squared": {
                "type": "number",
                "description": "Adjusted R-squared",
                "maximum": 1,
            },
            "f_statistic": {
                "type": "number",
                "description": "F-statistic for overall model significance",
            },
            "f_p_value": {
                "type": "number",
                "description": "P-value for F-statistic",
                "minimum": 0,
                "maximum": 1,
            },
            "residuals": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Model residuals",
            },
            "fitted_values": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Fitted/predicted values",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations",
                "minimum": 1,
            },
            "df_residual": {
                "type": "integer",
                "description": "Degrees of freedom for residuals",
            },
            "residual_se": {
                "type": "number",
                "description": "Residual standard error",
                "minimum": 0,
            },
            "method": {
                "type": "string",
                "description": "Estimation method used",
                "enum": ["lm"],
            },
        },
        "required": ["coefficients", "r_squared", "n_obs", "method"],
        "additionalProperties": False,
    },
    description="Performs ordinary least squares (OLS) linear regression to model relationships between a dependent variable and one or more predictors. Returns coefficients with standard errors, confidence intervals, R-squared, F-statistic, and comprehensive diagnostic statistics including residuals and fitted values. Use for prediction, inference, understanding linear relationships, or testing hypotheses about continuous outcomes. Handles missing values and supports weighted observations.",
)
async def linear_model(context, params) -> dict[str, Any]:
    """
    Fit ordinary least squares (OLS) linear regression model.

    This tool performs comprehensive linear regression analysis using R's lm() function.
    It supports weighted regression, missing value handling, and returns detailed
    model diagnostics including coefficients, significance tests, and goodness-of-fit.

    Args:
        context: Request execution context for logging and progress
        params: Dictionary containing:

            - data: Dataset as dict of column_name -> [values]
            - formula: R formula string (e.g., "y ~ x1 + x2")
            - weights: Optional array of observation weights
            - na_action: How to handle missing values ("na.omit", "na.exclude", "na.fail")

    Returns:
        Dictionary containing:

            - coefficients: Model coefficients by variable name
            - std_errors: Standard errors of coefficients
            - t_values: t-statistics for coefficient tests
            - p_values: p-values for coefficient significance
            - r_squared: Coefficient of determination
            - adj_r_squared: Adjusted R-squared
            - fstatistic: Overall F-statistic value
            - f_pvalue: p-value for overall model significance
            - residual_se: Residual standard error
            - fitted_values: Predicted values for each observation
            - residuals: Model residuals
            - n_obs: Number of observations used

    Example:
        >>> # Simple linear regression
        >>> data = {
        ...     "price": [100, 120, 140, 160, 180],
        ...     "size": [1000, 1200, 1400, 1600, 1800]
        ... }
        >>> result = await linear_model(context, {
        ...     "data": data,
        ...     "formula": "price ~ size"
        ... })
        >>> print(f"Price increases ${result['coefficients']['size']:.2f} per sq ft")
        >>> print(f"Model explains {result['r_squared']:.1%} of variance")
        >>> # Multiple regression with weights
        >>> data = {
        ...     "sales": [100, 150, 200, 250],
        ...     "advertising": [10, 20, 30, 40],
        ...     "price": [50, 45, 40, 35]
        ... }
        >>> result = await linear_model(context, {
        ...     "data": data,
        ...     "formula": "sales ~ advertising + price",
        ...     "weights": [1, 1, 2, 2]  # Weight later observations more
        ... })
    """
    await context.info("Fitting linear regression model")

    # Load R script from separated file
    r_script = get_r_script("regression", "linear_model")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "Linear model fitted successfully",
            r_squared=result.get("r_squared"),
            n_obs=result.get("n_obs"),
        )
        return result
    except Exception as e:
        await context.error("Linear model fitting failed", error=str(e))
        raise


@tool(
    name="correlation_analysis",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables to include in correlation analysis",
            },
            "method": {
                "type": "string",
                "enum": ["pearson", "spearman", "kendall"],
                "description": "Correlation method",
            },
            "use": {
                "type": "string",
                "enum": [
                    "everything",
                    "all.obs",
                    "complete.obs",
                    "na.or.complete",
                    "pairwise.complete.obs",
                ],
                "description": "Missing value handling",
            },
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "correlation_matrix": {
                "type": "object",
                "description": "Correlation coefficients between variables",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": {"type": "number"},
                },
            },
            "significance_tests": {
                "type": "object",
                "description": "P-values and test statistics for correlations",
                "properties": {
                    "p_values": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                        },
                    },
                    "test_statistics": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                        },
                    },
                },
            },
            "method": {
                "type": "string",
                "description": "Correlation method used",
                "enum": ["pearson", "spearman", "kendall"],
            },
            "n_obs": {
                "type": "object",
                "description": "Number of observations used for each correlation",
                "additionalProperties": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                },
            },
            "variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables included in the analysis",
            },
        },
        "required": ["correlation_matrix", "method", "variables"],
        "additionalProperties": False,
    },
    description="Computes pairwise correlation matrix between numeric variables using Pearson, Spearman, or Kendall methods. Provides correlation coefficients, significance tests (p-values), and handles missing data appropriately. Use to explore relationships between variables, identify multicollinearity, or understand data structure before modeling. Pearson for linear relationships, Spearman for monotonic non-linear relationships, Kendall for small samples or ties.",
)
async def correlation_analysis(context, params) -> dict[str, Any]:
    """
    Compute correlation matrix with significance testing.

    This tool calculates pairwise correlations between numeric variables using
    Pearson, Spearman, or Kendall methods. It includes significance tests for
    each correlation and handles missing values appropriately.

    Args:
        context: Request execution context for logging and progress
        params: Dictionary containing:

            - data: Dataset as dict of column_name -> [values]
            - variables: Optional list of variable names to include
            - method: Correlation method ("pearson", "spearman", "kendall")
            - use: Missing value handling strategy

    Returns:
        Dictionary containing:

            - correlation_matrix: Pairwise correlations as nested dict
            - significance_tests: p-values for each correlation
            - sample_sizes: Number of complete observations for each pair
            - variables_used: List of variables included in analysis
            - method_used: Correlation method applied

    Example:
        >>> # Basic correlation analysis
        >>> data = {
        ...     "sales": [100, 150, 200, 250, 300],
        ...     "advertising": [10, 20, 25, 35, 40],
        ...     "price": [50, 48, 45, 42, 40]
        ... }
        >>> result = await correlation_analysis(context, {
        ...     "data": data,
        ...     "method": "pearson"
        ... })
        >>> sales_ad_corr = result["correlation_matrix"]["sales"]["advertising"]
        >>> print(f"Sales-Advertising correlation: {sales_ad_corr:.3f}")
        >>> # Spearman correlation for non-linear relationships
        >>> result = await correlation_analysis(context, {
        ...     "data": data,
        ...     "method": "spearman",
        ...     "variables": ["sales", "advertising"]
        ... })
    """
    await context.info("Computing correlation matrix")

    # Load R script from separated file
    r_script = get_r_script("regression", "correlation_analysis")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "Correlation analysis completed",
            n_variables=len(result.get("variables", [])),
            method=result.get("method"),
        )
        return result
    except Exception as e:
        await context.error("Correlation analysis failed", error=str(e))
        raise


@tool(
    name="logistic_regression",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": formula_schema(),
            "family": {
                "type": "string",
                "enum": ["binomial", "poisson", "gamma", "inverse.gaussian"],
                "description": "Error distribution family",
            },
            "link": {
                "type": "string",
                "enum": ["logit", "probit", "cloglog", "cauchit"],
                "description": "Link function for binomial family",
            },
        },
        "required": ["data", "formula"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "coefficients": {
                "type": "object",
                "description": "Model coefficients by variable name",
                "additionalProperties": {"type": "number"},
            },
            "std_errors": {
                "type": "object",
                "description": "Standard errors of coefficients",
                "additionalProperties": {"type": "number"},
            },
            "z_values": {
                "type": "object",
                "description": "Z-statistics for coefficients",
                "additionalProperties": {"type": "number"},
            },
            "p_values": {
                "type": "object",
                "description": "P-values for coefficient significance tests",
                "additionalProperties": {"type": "number"},
            },
            "deviance": {
                "type": "number",
                "description": "Residual deviance of the model",
            },
            "null_deviance": {
                "type": "number",
                "description": "Null deviance of the model",
            },
            "aic": {"type": "number", "description": "Akaike Information Criterion"},
            "bic": {"type": "number", "description": "Bayesian Information Criterion"},
            "fitted_values": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Fitted/predicted values",
            },
            "residuals": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Deviance residuals",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations",
                "minimum": 1,
            },
            "family": {
                "type": "string",
                "description": "Error distribution family used",
                "enum": ["binomial", "poisson", "gamma", "inverse.gaussian"],
            },
            "link": {"type": "string", "description": "Link function used"},
            "odds_ratios": {
                "type": "object",
                "description": "Odds ratios for binomial models",
                "additionalProperties": {"type": "number"},
            },
            "mcfadden_r_squared": {
                "type": "number",
                "description": "McFadden's pseudo R-squared for binomial models",
                "minimum": 0,
                "maximum": 1,
            },
            "predicted_probabilities": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Predicted probabilities for binomial models",
            },
            "accuracy": {
                "type": "number",
                "description": "Classification accuracy for binary models",
                "minimum": 0,
                "maximum": 1,
            },
            "confusion_matrix": {
                "type": "object",
                "description": "Confusion matrix for binary classification",
                "additionalProperties": {"type": "array"},
            },
        },
        "required": [
            "coefficients",
            "deviance",
            "null_deviance",
            "aic",
            "bic",
            "n_obs",
            "family",
            "link",
        ],
        "additionalProperties": False,
    },
    description="Fits generalized linear models (GLM) including logistic regression for binary outcomes, Poisson regression for count data, and other exponential family distributions. Returns coefficients, odds ratios (for logistic), AIC/BIC for model comparison, and diagnostic statistics. Use for binary classification, count modeling, or when dependent variable doesn't follow normal distribution. Includes prediction probabilities and confusion matrix for classification tasks.",
)
async def logistic_regression(context, params) -> dict[str, Any]:
    """Fit logistic regression model."""
    await context.info("Fitting logistic regression model")

    # Load R script from separated file
    r_script = get_r_script("regression", "logistic_regression")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "Logistic regression fitted successfully",
            aic=result.get("aic"),
            n_obs=result.get("n_obs"),
        )
        return result
    except Exception as e:
        await context.error("Logistic regression fitting failed", error=str(e))
        raise
