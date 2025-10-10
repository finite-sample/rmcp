"""
Descriptive statistics tools for RMCP.
Comprehensive data exploration and summary capabilities.
"""

from typing import Any

from ..core.schemas import table_schema
from ..r_assets.loader import get_r_script
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="summary_stats",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "group_by": {"type": "string"},
            "percentiles": {
                "type": "array",
                "items": {"type": "number"},
                "default": [0.25, 0.5, 0.75],
            },
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "statistics": {
                "type": "object",
                "description": "Comprehensive statistics by variable or group",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "n": {"type": "integer", "minimum": 0},
                        "n_missing": {"type": "integer", "minimum": 0},
                        "mean": {"type": "number"},
                        "sd": {"type": "number"},
                        "min": {"type": "number"},
                        "max": {"type": "number"},
                        "range": {"type": "number"},
                        "skewness": {"type": "number"},
                        "kurtosis": {"type": "number"},
                    },
                },
            },
            "variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables included in analysis",
            },
            "n_obs": {
                "type": "integer",
                "description": "Total number of observations",
                "minimum": 0,
            },
            "grouped": {
                "type": "boolean",
                "description": "Whether statistics are grouped",
            },
            "group_by": {
                "type": "string",
                "description": "Grouping variable if applicable",
            },
            "groups": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Group levels if grouped analysis",
            },
        },
        "required": ["statistics", "variables", "n_obs", "grouped"],
        "additionalProperties": False,
    },
    description="Computes comprehensive descriptive statistics including mean, median, standard deviation, quantiles, skewness, kurtosis, and distribution shape measures. Supports grouping by categorical variables for comparative analysis. Provides missing value counts and handles different data types appropriately. Use for initial data exploration, understanding variable distributions, identifying data quality issues, or generating summary reports for research and business analytics.",
)
async def summary_stats(context, params) -> dict[str, Any]:
    """Compute comprehensive descriptive statistics."""
    await context.info("Computing summary statistics")

    r_script = get_r_script("descriptive", "summary_stats")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Summary statistics computed successfully")
        return result
    except Exception as e:
        await context.error("Summary statistics failed", error=str(e))
        raise


@tool(
    name="outlier_detection",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "method": {
                "type": "string",
                "enum": ["iqr", "z_score", "modified_z"],
                "default": "iqr",
            },
            "threshold": {"type": "number", "minimum": 0, "default": 3.0},
        },
        "required": ["data", "variable"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["iqr", "z_score", "modified_z"],
                "description": "Outlier detection method used",
            },
            "variable": {
                "type": "string",
                "description": "Variable analyzed for outliers",
            },
            "outlier_indices": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Row indices of outliers (1-based)",
            },
            "outlier_values": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Actual outlier values",
            },
            "n_outliers": {
                "type": "integer",
                "description": "Number of outliers detected",
                "minimum": 0,
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of valid observations",
                "minimum": 0,
            },
            "outlier_percentage": {
                "type": "number",
                "description": "Percentage of observations that are outliers",
                "minimum": 0,
                "maximum": 100,
            },
            "bounds": {
                "type": "object",
                "description": "Detection bounds and parameters used",
                "additionalProperties": {"type": "number"},
            },
        },
        "required": [
            "method",
            "variable",
            "outlier_indices",
            "outlier_values",
            "n_outliers",
            "n_obs",
            "outlier_percentage",
            "bounds",
        ],
        "additionalProperties": False,
    },
    description="Identifies outliers using multiple detection methods: Interquartile Range (IQR) method, Z-score (standard deviations from mean), Modified Z-score (using median absolute deviation), or Mahalanobis distance for multivariate outliers. Returns outlier flags, detection thresholds, and visualization-ready results. Use for data cleaning, quality assessment, fraud detection, or preparing data for modeling by identifying unusual observations.",
)
async def outlier_detection(context, params) -> dict[str, Any]:
    """Detect outliers in data."""
    await context.info("Detecting outliers")

    r_script = get_r_script("descriptive", "outlier_detection")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Outlier detection completed successfully")
        return result
    except Exception as e:
        await context.error("Outlier detection failed", error=str(e))
        raise


@tool(
    name="frequency_table",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "include_percentages": {"type": "boolean", "default": True},
            "sort_by": {
                "type": "string",
                "enum": ["frequency", "value"],
                "default": "frequency",
            },
        },
        "required": ["data", "variables"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "frequency_tables": {
                "type": "object",
                "description": "Frequency tables by variable",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "values": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Unique values in the variable",
                        },
                        "frequencies": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Count of each value",
                        },
                        "percentages": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Percentage of each value",
                        },
                        "n_total": {
                            "type": "integer",
                            "description": "Total valid observations",
                            "minimum": 0,
                        },
                        "n_missing": {
                            "type": "integer",
                            "description": "Number of missing values",
                            "minimum": 0,
                        },
                        "missing_percentage": {
                            "type": "number",
                            "description": "Percentage of missing values",
                            "minimum": 0,
                            "maximum": 100,
                        },
                    },
                    "required": ["values", "frequencies", "n_total"],
                },
            },
            "variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables analyzed",
            },
            "total_observations": {
                "type": "integer",
                "description": "Total number of observations in dataset",
                "minimum": 0,
            },
        },
        "required": ["frequency_tables", "variables", "total_observations"],
        "additionalProperties": False,
    },
    description="Creates frequency tables for categorical variables showing counts, percentages, cumulative frequencies, and missing value summaries. Supports multiple variables simultaneously and optional sorting by frequency or value. Provides chi-square goodness-of-fit tests when expected frequencies are specified. Use for categorical data exploration, survey analysis, market research, or understanding distribution of discrete variables.",
)
async def frequency_table(context, params) -> dict[str, Any]:
    """Generate frequency tables."""
    await context.info("Creating frequency tables")

    r_script = get_r_script("descriptive", "frequency_table")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info("Frequency tables created successfully")
        return result
    except Exception as e:
        await context.error("Frequency table creation failed", error=str(e))
        raise
