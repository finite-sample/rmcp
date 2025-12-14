"""
Statistical hypothesis testing tools for RMCP.
Comprehensive statistical testing capabilities.
"""

from typing import Any

from ..core.schemas import table_schema
from ..r_assets.loader import get_r_script
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="t_test",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "group": {
                "type": "string",
                "description": (
                    "Required for two-sample t-test. Column name for group variable. "
                    "Omit for one-sample t-test."
                ),
            },
            "mu": {"type": "number", "default": 0},
            "alternative": {
                "type": "string",
                "enum": ["two.sided", "less", "greater"],
                "default": "two.sided",
            },
            "paired": {"type": "boolean", "default": False},
            "var_equal": {"type": "boolean", "default": False},
        },
        "required": ["data", "variable"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "test_type": {
                "type": "string",
                "description": "Type of t-test performed",
                "enum": [
                    "One-sample t-test",
                    "Paired t-test",
                    "Two-sample t-test (equal variances)",
                    "Welch's t-test",
                ],
            },
            "statistic": {"type": "number", "description": "t-statistic value"},
            "df": {"type": "number", "description": "Degrees of freedom", "minimum": 0},
            "p_value": {
                "type": "number",
                "description": "P-value of the test",
                "minimum": 0,
                "maximum": 1,
            },
            "confidence_interval": {
                "type": "object",
                "properties": {
                    "lower": {"type": "number"},
                    "upper": {"type": "number"},
                    "level": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "description": "Confidence interval for the mean difference",
            },
            "alternative": {
                "type": "string",
                "enum": ["two.sided", "less", "greater"],
                "description": "Alternative hypothesis",
            },
            "mean": {"type": "number", "description": "Sample mean (one-sample test)"},
            "null_value": {
                "type": "number",
                "description": "Null hypothesis value (one-sample test)",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations (one-sample test)",
                "minimum": 1,
            },
            "mean_x": {
                "type": "number",
                "description": "Mean of group x (two-sample test)",
            },
            "mean_y": {
                "type": "number",
                "description": "Mean of group y (two-sample test)",
            },
            "mean_difference": {
                "type": "number",
                "description": "Difference between group means (two-sample test)",
            },
            "groups": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Group levels (two-sample test)",
            },
            "paired": {
                "type": "boolean",
                "description": "Whether test was paired (two-sample test)",
            },
            "var_equal": {
                "type": "boolean",
                "description": "Whether equal variances assumed (two-sample test)",
            },
            "n_obs_x": {
                "type": "integer",
                "description": "Number of observations in group x (two-sample test)",
                "minimum": 1,
            },
            "n_obs_y": {
                "type": "integer",
                "description": "Number of observations in group y (two-sample test)",
                "minimum": 1,
            },
        },
        "required": [
            "test_type",
            "statistic",
            "df",
            "p_value",
            "confidence_interval",
            "alternative",
        ],
        "additionalProperties": False,
    },
    description="Performs Student's t-tests to compare means: one-sample (test if mean equals hypothesized value), two-sample (compare means between groups), or paired (compare before/after measurements). Returns t-statistic, degrees of freedom, p-value, confidence intervals, and effect size. Use for hypothesis testing about population means, comparing group differences, or analyzing experimental results. Handles equal/unequal variances and provides Cohen's d effect size.",
)
async def t_test(context, params) -> dict[str, Any]:
    """Perform t-test analysis."""
    await context.info("Performing t-test")

    # Load R script from separated file
    r_script = get_r_script("statistical_tests", "t_test")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("T-test completed successfully")
        return result
    except Exception as e:
        await context.error("T-test failed", error=str(e))
        raise


@tool(
    name="anova",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": {"type": "string"},
            "type": {"type": "string", "enum": ["I", "II", "III"], "default": "I"},
        },
        "required": ["data", "formula"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "anova_table": {
                "type": "object",
                "properties": {
                    "terms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Model terms/factors",
                    },
                    "df": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Degrees of freedom",
                    },
                    "sum_sq": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Sum of squares",
                    },
                    "mean_sq": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Mean squares",
                    },
                    "f_value": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "F-statistics",
                    },
                    "p_value": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "P-values",
                    },
                },
                "description": "ANOVA table with test statistics",
            },
            "model_summary": {
                "type": "object",
                "properties": {
                    "r_squared": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "R-squared value",
                    },
                    "adj_r_squared": {
                        "type": "number",
                        "maximum": 1,
                        "description": "Adjusted R-squared value",
                    },
                    "residual_se": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Residual standard error",
                    },
                    "df_residual": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Residual degrees of freedom",
                    },
                    "n_obs": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Number of observations",
                    },
                },
                "description": "Overall model fit statistics",
            },
            "formula": {"type": "string", "description": "Model formula used"},
            "anova_type": {
                "type": "string",
                "description": "Type of ANOVA performed",
                "enum": ["Type I", "Type II", "Type III"],
            },
        },
        "required": ["anova_table", "model_summary", "formula", "anova_type"],
        "additionalProperties": False,
    },
    description="Performs Analysis of Variance (ANOVA) to test for significant differences between group means. Supports one-way ANOVA (single factor), two-way ANOVA (two factors with interaction), and repeated measures designs. Returns F-statistics, p-values, effect sizes (eta-squared), and post-hoc comparisons when significant. Use when comparing means across 3+ groups, testing factorial designs, or analyzing experimental data with multiple conditions.",
)
async def anova(context, params) -> dict[str, Any]:
    """Perform ANOVA analysis."""
    await context.info("Performing ANOVA")

    # Load R script from separated file
    r_script = get_r_script("statistical_tests", "anova")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("ANOVA completed successfully")
        return result
    except Exception as e:
        await context.error("ANOVA failed", error=str(e))
        raise


@tool(
    name="chi_square_test",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "test_type": {
                "type": "string",
                "enum": ["independence", "goodness_of_fit"],
                "description": "Type of chi-square test",
            },
            "x": {
                "type": "string",
                "description": "First variable (or only variable for goodness of fit)",
            },
            "y": {
                "type": "string",
                "description": "Second variable (required for independence test)",
            },
            "expected": {
                "type": "array",
                "items": {"type": "number", "minimum": 0},
                "minItems": 1,
                "description": "Expected frequencies (for goodness of fit test)",
            },
        },
        "required": ["data", "test_type", "x"],
        "additionalProperties": False,
    },
    output_schema={
        "type": "object",
        "properties": {
            "test_type": {
                "type": "string",
                "description": "Type of chi-square test performed",
                "enum": [
                    "Chi-square test of independence",
                    "Chi-square goodness of fit test",
                ],
            },
            "statistic": {
                "type": "number",
                "description": "Chi-square test statistic",
                "minimum": 0,
            },
            "df": {"type": "number", "description": "Degrees of freedom", "minimum": 0},
            "p_value": {
                "type": "number",
                "description": "P-value of the test",
                "minimum": 0,
                "maximum": 1,
            },
            "expected_frequencies": {
                "type": "array",
                "description": "Expected frequencies under null hypothesis",
                "items": {"type": "array", "items": {"type": "number"}},
            },
            "residuals": {
                "type": "array",
                "description": "Standardized residuals",
                "items": {"type": "array", "items": {"type": "number"}},
            },
            "contingency_table": {
                "type": "array",
                "description": "Observed contingency table (independence test)",
                "items": {"type": "array", "items": {"type": "number"}},
            },
            "x_variable": {
                "type": "string",
                "description": "X variable name (independence test)",
            },
            "y_variable": {
                "type": "string",
                "description": "Y variable name (independence test)",
            },
            "cramers_v": {
                "type": "number",
                "description": "Cramer's V effect size (independence test)",
                "minimum": 0,
                "maximum": 1,
            },
            "observed_frequencies": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Observed frequencies (goodness of fit test)",
            },
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Category names (goodness of fit test)",
            },
        },
        "required": [
            "test_type",
            "statistic",
            "df",
            "p_value",
            "expected_frequencies",
            "residuals",
        ],
        "additionalProperties": False,
    },
    description="Performs chi-square tests for categorical data analysis: test of independence (relationship between two categorical variables) and goodness-of-fit (whether data follows expected distribution). Returns chi-square statistic, degrees of freedom, p-value, expected frequencies, and standardized residuals. Use for analyzing contingency tables, testing associations between categorical variables, or validating theoretical distributions against observed data.",
)
async def chi_square_test(context, params) -> dict[str, Any]:
    """Perform chi-square tests."""
    await context.info("Performing chi-square test")

    # Load R script from separated file
    r_script = get_r_script("statistical_tests", "chi_square_test")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Chi-square test completed successfully")
        return result
    except Exception as e:
        await context.error("Chi-square test failed", error=str(e))
        raise


@tool(
    name="normality_test",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "test": {
                "type": "string",
                "enum": ["shapiro", "jarque_bera", "anderson"],
                "default": "shapiro",
            },
        },
        "required": ["data", "variable"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "test_name": {
                "type": "string",
                "description": "Name of the normality test performed",
                "enum": [
                    "Shapiro-Wilk normality test",
                    "Jarque-Bera normality test",
                    "Anderson-Darling normality test",
                ],
            },
            "statistic": {"type": "number", "description": "Test statistic value"},
            "df": {
                "type": "number",
                "description": "Degrees of freedom (Jarque-Bera only)",
                "minimum": 0,
            },
            "p_value": {
                "type": "number",
                "description": "P-value of the test",
                "minimum": 0,
                "maximum": 1,
            },
            "is_normal": {
                "type": "boolean",
                "description": "Whether data appears normal (p > 0.05)",
            },
            "variable": {
                "type": "string",
                "description": "Variable tested for normality",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of valid observations",
                "minimum": 1,
            },
            "mean": {"type": "number", "description": "Sample mean"},
            "sd": {
                "type": "number",
                "description": "Sample standard deviation",
                "minimum": 0,
            },
            "skewness": {"type": "number", "description": "Sample skewness"},
            "excess_kurtosis": {
                "type": "number",
                "description": "Excess kurtosis (normal distribution = 0)",
            },
        },
        "required": [
            "test_name",
            "statistic",
            "p_value",
            "is_normal",
            "variable",
            "n_obs",
            "mean",
            "sd",
            "skewness",
            "excess_kurtosis",
        ],
        "additionalProperties": False,
    },
    description="Tests variables for normal distribution using multiple methods: Shapiro-Wilk (most powerful for small samples), Kolmogorov-Smirnov, Anderson-Darling, or Jarque-Bera tests. Returns test statistics, p-values, and clear interpretation for each test. Use before parametric statistical analyzes, to validate model assumptions, or to choose appropriate statistical methods. Critical for regression diagnostics and assumption checking.",
)
async def normality_test(context, params) -> dict[str, Any]:
    """Test for normality."""
    await context.info("Testing for normality")

    # Load R script from separated file
    r_script = get_r_script("statistical_tests", "normality_test")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Normality test completed successfully")
        return result
    except Exception as e:
        await context.error("Normality test failed", error=str(e))
        raise
