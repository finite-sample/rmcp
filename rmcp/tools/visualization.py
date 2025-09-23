"""
Visualization tools for RMCP.
Statistical plotting and data visualization capabilities.
"""

from typing import Any

from ..core.schemas import formula_schema, table_schema
from ..r_assets.loader import get_r_script
from ..r_integration import execute_r_script_with_image_async
from ..registries.tools import tool


@tool(
    name="scatter_plot",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "x": {"type": "string"},
            "y": {"type": "string"},
            "group": {"type": ["string", "null"], "default": None},
            "title": {"type": "string"},
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 600},
        },
        "required": ["data", "x", "y"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["scatter"],
                "description": "Type of plot generated",
            },
            "variables": {
                "type": "object",
                "properties": {
                    "x": {"type": "string"},
                    "y": {"type": "string"},
                    "group": {"type": ["string", "null"]},
                },
                "required": ["x", "y"],
                "description": "Variables plotted",
            },
            "statistics": {
                "type": "object",
                "properties": {
                    "correlation": {"type": "number"},
                    "n_points": {"type": "integer"},
                    "trend_line": {
                        "type": "object",
                        "properties": {
                            "slope": {"type": "number"},
                            "intercept": {"type": "number"},
                            "r_squared": {"type": "number"},
                        },
                    },
                },
                "description": "Statistical summary of the plot",
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": ["plot_type", "variables"],
    },
    description="Create scatter plot with optional grouping and trend lines",
)
async def scatter_plot(context, params) -> dict[str, Any]:
    """Create scatter plot."""
    await context.info("Creating scatter plot")
    r_script = get_r_script("visualization", "scatter_plot")
    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 800)
        height = params.get("height", 600)
        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )
        await context.info("Scatter plot created successfully")
        return result
    except Exception as e:
        await context.error("Scatter plot creation failed", error=str(e))
        raise


@tool(
    name="histogram",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "group": {"type": ["string", "null"], "default": None},
            "bins": {"type": "integer", "minimum": 5, "maximum": 100, "default": 30},
            "title": {"type": "string"},
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 600},
        },
        "required": ["data", "variable"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["histogram"],
                "description": "Type of plot generated",
            },
            "variable": {
                "type": "string",
                "description": "Variable analyzed in histogram",
            },
            "group_variable": {
                "type": ["string", "null"],
                "description": "Grouping variable if specified",
            },
            "bins": {
                "type": "integer",
                "description": "Number of bins used in histogram",
            },
            "statistics": {
                "type": "object",
                "properties": {
                    "mean": {"type": "number"},
                    "median": {"type": "number"},
                    "sd": {"type": "number"},
                    "skewness": {"type": "number"},
                    "kurtosis": {"type": "number"},
                },
                "description": "Descriptive statistics for the variable",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of valid observations",
                "minimum": 0,
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": ["plot_type", "variable", "bins", "statistics", "n_obs"],
    },
    description="Create histogram with optional grouping and density overlay",
)
async def histogram(context, params) -> dict[str, Any]:
    """Create histogram."""
    await context.info("Creating histogram")
    r_script = get_r_script("visualization", "histogram")
    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 800)
        height = params.get("height", 600)
        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )
        await context.info("Histogram created successfully")
        return result
    except Exception as e:
        await context.error("Histogram creation failed", error=str(e))
        raise


@tool(
    name="boxplot",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variable": {"type": "string"},
            "group": {"type": ["string", "null"], "default": None},
            "title": {"type": "string"},
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 600},
        },
        "required": ["data", "variable"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["boxplot"],
                "description": "Type of plot generated",
            },
            "variable": {
                "type": "string",
                "description": "Variable analyzed in boxplot",
            },
            "group_variable": {
                "type": ["string", "null"],
                "description": "Grouping variable if specified",
            },
            "summary_statistics": {
                "type": "object",
                "description": "Quartile statistics by group or overall",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "median": {"type": "number"},
                        "q1": {"type": "number"},
                        "q3": {"type": "number"},
                        "iqr": {"type": "number"},
                        "n": {"type": "integer"},
                        "outliers": {"type": "integer"},
                    },
                },
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": ["plot_type", "variable", "summary_statistics"],
    },
    description="Create box plot with optional grouping",
)
async def boxplot(context, params) -> dict[str, Any]:
    """Create box plot."""
    await context.info("Creating box plot")
    r_script = get_r_script("visualization", "boxplot")
    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 800)
        height = params.get("height", 600)
        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )
        await context.info("Box plot created successfully")
        return result
    except Exception as e:
        await context.error("Box plot creation failed", error=str(e))
        raise


@tool(
    name="time_series_plot",
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
            "title": {"type": "string"},
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "show_trend": {"type": "boolean", "default": True},
            "width": {"type": "integer", "minimum": 100, "default": 1000},
            "height": {"type": "integer", "minimum": 100, "default": 600},
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["time_series_plot"],
                "description": "Type of plot generated",
            },
            "statistics": {
                "type": "object",
                "properties": {
                    "mean": {"type": "number"},
                    "sd": {"type": "number"},
                    "min": {"type": "number"},
                    "max": {"type": "number"},
                    "range": {"type": "number"},
                    "n_obs": {"type": "integer"},
                },
                "description": "Time series descriptive statistics",
            },
            "has_dates": {
                "type": "boolean",
                "description": "Whether date information was provided",
            },
            "show_trend": {
                "type": "boolean",
                "description": "Whether trend line was included",
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": ["plot_type", "statistics", "has_dates", "show_trend"],
    },
    description="Create time series plot with optional trend line",
)
async def time_series_plot(context, params) -> dict[str, Any]:
    """Create time series plot."""
    await context.info("Creating time series plot")
    r_script = get_r_script("visualization", "time_series_plot")
    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 1000)
        height = params.get("height", 600)
        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )
        await context.info("Time series plot created successfully")
        return result
    except Exception as e:
        await context.error("Time series plot creation failed", error=str(e))
        raise


@tool(
    name="correlation_heatmap",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "method": {
                "type": "string",
                "enum": ["pearson", "spearman", "kendall"],
                "default": "pearson",
            },
            "title": {"type": "string"},
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "width": {"type": "integer", "minimum": 100, "default": 800},
            "height": {"type": "integer", "minimum": 100, "default": 800},
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["heatmap"],
                "description": "Type of plot generated",
            },
            "correlation_matrix": {
                "type": "object",
                "description": "Correlation coefficients between variables",
                "additionalProperties": {"type": "array", "items": {"type": "number"}},
            },
            "variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables included in correlation matrix",
            },
            "method": {
                "type": "string",
                "enum": ["pearson", "spearman", "kendall"],
                "description": "Correlation method used",
            },
            "n_variables": {
                "type": "integer",
                "description": "Number of variables in correlation matrix",
                "minimum": 2,
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": [
            "plot_type",
            "correlation_matrix",
            "variables",
            "method",
            "n_variables",
        ],
    },
    description="Create correlation heatmap matrix",
)
async def correlation_heatmap(context, params) -> dict[str, Any]:
    """Create correlation heatmap."""
    await context.info("Creating correlation heatmap")
    r_script = get_r_script("visualization", "correlation_heatmap")
    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 800)
        height = params.get("height", 800)
        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )
        await context.info("Correlation heatmap created successfully")
        return result
    except Exception as e:
        await context.error("Correlation heatmap creation failed", error=str(e))
        raise


@tool(
    name="regression_plot",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": formula_schema(),
            "title": {"type": "string"},
            "file_path": {
                "type": "string",
                "description": "Optional: Save plot to this file",
            },
            "return_image": {
                "type": "boolean",
                "default": True,
                "description": "Return image data for inline display",
            },
            "residual_plots": {"type": "boolean", "default": True},
            "width": {"type": "integer", "minimum": 100, "default": 1200},
            "height": {"type": "integer", "minimum": 100, "default": 800},
        },
        "required": ["data", "formula"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "plot_type": {
                "type": "string",
                "enum": ["regression_plot"],
                "description": "Type of plot generated",
            },
            "r_squared": {
                "type": "number",
                "description": "R-squared value of the regression model",
                "minimum": 0,
                "maximum": 1,
            },
            "adj_r_squared": {
                "type": "number",
                "description": "Adjusted R-squared value",
                "maximum": 1,
            },
            "residual_se": {
                "type": "number",
                "description": "Residual standard error",
                "minimum": 0,
            },
            "formula": {"type": "string", "description": "Regression formula used"},
            "residual_plots": {
                "type": "boolean",
                "description": "Whether diagnostic plots were generated",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations in the model",
                "minimum": 1,
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                },
                "description": "Plot dimensions in pixels",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded PNG image data",
            },
            "image_mime_type": {
                "type": "string",
                "enum": ["image/png"],
                "description": "MIME type of the image",
            },
        },
        "required": [
            "plot_type",
            "r_squared",
            "adj_r_squared",
            "residual_se",
            "formula",
            "residual_plots",
            "n_obs",
        ],
    },
    description="Create regression diagnostic plots (fitted vs residuals, Q-Q plot, etc.)",
)
async def regression_plot(context, params) -> dict[str, Any]:
    """Create regression diagnostic plots."""
    await context.info("Creating regression plots")
    r_script = get_r_script("visualization", "regression_plot")
    try:
        # Use the new image-enabled function
        return_image = params.get("return_image", True)
        width = params.get("width", 1200)
        height = params.get("height", 800)
        result = await execute_r_script_with_image_async(
            r_script,
            params,
            include_image=return_image,
            image_width=width,
            image_height=height,
        )
        await context.info("Regression plots created successfully")
        return result
    except Exception as e:
        await context.error("Regression plot creation failed", error=str(e))
        raise
