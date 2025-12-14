"""
Error Recovery and Helper Tools for RMCP.
Intelligent error diagnosis, data validation, and recovery suggestions.
"""

import re
from typing import Any

from ..r_assets.loader import get_r_script
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="suggest_fix",
    input_schema={
        "type": "object",
        "properties": {
            "error_message": {
                "type": "string",
                "description": "Error message or description of the problem",
            },
            "tool_name": {
                "type": "string",
                "description": "Name of the tool that failed",
            },
            "data": {
                "type": "object",
                "description": "Optional data that caused the error",
            },
            "parameters": {
                "type": "object",
                "description": "Optional parameters that were used",
            },
        },
        "required": ["error_message"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "error_type": {
                "type": "string",
                "enum": [
                    "missing_package",
                    "missing_variable",
                    "formula_syntax",
                    "file_not_found",
                    "data_type",
                    "missing_values",
                    "memory_size",
                    "general",
                ],
                "description": "Categorized type of error",
            },
            "suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Actionable suggestions to fix the error",
            },
            "data_suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Data-specific suggestions based on analysis",
            },
            "next_steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Recommended next steps to resolve the issue",
            },
            "documentation_links": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Relevant documentation and help links",
            },
            "quick_fixes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Quick fix commands or code snippets",
            },
        },
        "required": [
            "error_type",
            "suggestions",
            "data_suggestions",
            "next_steps",
            "documentation_links",
            "quick_fixes",
        ],
        "additionalProperties": False,
    },
    description="Analyzes error messages from statistical operations and provides intelligent, actionable suggestions for fixes including parameter adjustments, data transformations, or alternative approaches. Uses pattern matching and statistical knowledge to diagnose common issues. Use when statistical analyzes fail, to help users understand error causes, debug complex workflows, or learn proper statistical software usage through guided error resolution.",
)
async def suggest_fix(context, params) -> dict[str, Any]:
    """Analyze error and provide actionable solutions."""
    error_message = params["error_message"]
    tool_name = params.get("tool_name", "unknown")
    data = params.get("data")
    await context.info("Analyzing error", error=error_message, tool=tool_name)
    # Pattern-based error analysis
    suggestions = []
    error_type = "general"
    # R package errors
    if "there is no package called" in error_message:
        match = re.search(
            r"there is no package called ['\"]([^'\"]+)['\"]", error_message
        )
        if match:
            missing_pkg = match.group(1)
            error_type = "missing_package"
            suggestions = [
                f'Install the missing R package: install.packages("{missing_pkg}")',
                "Run 'rmcp check-r-packages' to see all missing packages",
                "Install all RMCP packages at once with the command in documentation",
            ]
    # Data format errors
    elif "object" in error_message.lower() and "not found" in error_message.lower():
        error_type = "missing_variable"
        suggestions = [
            "Check that all variable names in your formula exist in the data",
            "Use data_info tool to see available variables in your dataset",
            "Verify spelling of variable names (R is case-sensitive)",
        ]
    # Formula errors
    elif "invalid formula" in error_message.lower() or "~" in error_message:
        error_type = "formula_syntax"
        suggestions = [
            "Check formula syntax: outcome ~ predictor1 + predictor2",
            "Use build_formula tool for natural language formula creation",
            "Ensure variable names don't contain spaces or special characters",
        ]
    # File not found errors
    elif (
        "file not found" in error_message.lower()
        or "no such file" in error_message.lower()
    ):
        error_type = "file_not_found"
        suggestions = [
            "Check that the file path is correct and the file exists",
            "Use absolute paths or ensure the file is in the current directory",
            "Verify file permissions (read access required)",
        ]
    # Data type errors
    elif (
        "invalid type" in error_message.lower()
        or "non-numeric" in error_message.lower()
    ):
        error_type = "data_type"
        suggestions = [
            "Check that numeric operations are performed on numeric variables",
            "Convert character variables to factors or numeric as appropriate",
            "Use data_info tool to check variable types in your dataset",
        ]
    # Missing value errors
    elif "missing values" in error_message.lower() or "na" in error_message.lower():
        error_type = "missing_values"
        suggestions = [
            "Handle missing values before analysis (remove or impute)",
            "Use na.omit() in R or filter out missing values",
            "Check data quality with data_info tool",
        ]
    # Memory or size errors
    elif "memory" in error_message.lower() or "too large" in error_message.lower():
        error_type = "memory_size"
        suggestions = [
            "Try working with a smaller subset of your data first",
            "Use sampling to reduce dataset size for initial analysis",
            "Consider using more memory-efficient methods",
        ]
    # Generic suggestions if no specific pattern matched
    if not suggestions:
        suggestions = [
            "Check the documentation for the specific tool you're using",
            "Verify that your data format matches the tool's requirements",
            "Try a simpler version of your analysis first",
            "Use validate_data tool to check your dataset for common issues",
        ]
    # Add tool-specific suggestions
    tool_specific_suggestions = _get_tool_specific_suggestions(tool_name, error_message)
    suggestions.extend(tool_specific_suggestions)
    # Data-specific suggestions if data provided
    data_suggestions = []
    if data:
        try:
            data_analysis = await _analyze_data_for_errors(context, data)
            data_suggestions = data_analysis.get("suggestions", [])
        except Exception:
            pass
    result = {
        "error_type": error_type,
        "suggestions": suggestions[:10],  # Limit to top 10
        "data_suggestions": data_suggestions,
        "next_steps": _get_next_steps(error_type, tool_name),
        "documentation_links": _get_documentation_links(tool_name, error_type),
        "quick_fixes": _get_quick_fixes(error_type),
    }
    await context.info(
        "Error analysis completed",
        error_type=error_type,
        suggestions_count=len(suggestions),
    )
    return result


def _get_tool_specific_suggestions(tool_name: str, error_message: str) -> list[str]:
    """Get suggestions specific to the tool that failed."""
    tool_suggestions = {
        "linear_model": [
            "Ensure you have at least 2 data points for regression",
            "Check that outcome variable is numeric",
            "Verify predictor variables exist in the data",
        ],
        "logistic_regression": [
            "Outcome variable should be binary (0/1) or factor",
            "Ensure you have both positive and negative cases",
            "Check for complete separation in your data",
        ],
        "correlation_analysis": [
            "All variables should be numeric for correlation analysis",
            "Remove or handle missing values before correlation",
            "Ensure you have at least 3 observations",
        ],
        "read_csv": [
            "Check file path and file exists",
            "Verify CSV format and delimiter",
            "Ensure file has proper headers if header=True",
        ],
        "arima_model": [
            "Time series should be numeric and regularly spaced",
            "Check for missing values in time series",
            "Ensure sufficient data points (>20 recommended)",
        ],
    }
    return tool_suggestions.get(tool_name, [])


def _get_next_steps(error_type: str, tool_name: str) -> list[str]:
    """Get recommended next steps based on error type."""
    next_steps_map = {
        "missing_package": [
            "Install missing R packages",
            "Run rmcp check-r-packages",
            "Retry the analysis",
        ],
        "missing_variable": [
            "Use data_info tool to explore your dataset",
            "Check variable names and spelling",
            "Verify data was loaded correctly",
        ],
        "formula_syntax": [
            "Use build_formula tool for help",
            "Check R formula documentation",
            "Start with simpler formula",
        ],
        "file_not_found": [
            "Verify file path",
            "Check file permissions",
            "Try absolute path",
        ],
        "data_type": [
            "Use data_info to check variable types",
            "Convert variables to appropriate types",
            "Clean data before analysis",
        ],
    }
    return next_steps_map.get(
        error_type,
        [
            "Review error message carefully",
            "Check tool documentation",
            "Try simpler approach first",
        ],
    )


def _get_documentation_links(tool_name: str, error_type: str) -> list[str]:
    """Get relevant documentation links."""
    base_docs = [
        "Quick Start Guide: examples/quick_start_guide.md",
        "README: README.md",
    ]
    if tool_name in ["linear_model", "logistic_regression"]:
        base_docs.append("R regression documentation: ?lm, ?glm")
    elif tool_name in ["correlation_analysis"]:
        base_docs.append("R correlation documentation: ?cor")
    elif error_type == "missing_package":
        base_docs.append("R package installation: install.packages()")
    return base_docs


def _get_quick_fixes(error_type: str) -> list[str]:
    """Get quick fix commands for common errors."""
    quick_fixes = {
        "missing_package": [
            'install.packages(c("jsonlite", "plm", "lmtest", "sandwich", "AER"))',
            "rmcp check-r-packages",
        ],
        "missing_variable": [
            "Use build_formula tool to create correct formula",
            "Check data with data_info tool",
        ],
        "formula_syntax": [
            'Try simple formula like: "y ~ x"',
            "Use build_formula tool for natural language input",
        ],
        "data_type": [
            "Convert to numeric: as.numeric(variable)",
            "Convert to factor: as.factor(variable)",
        ],
    }
    return quick_fixes.get(error_type, [])


async def _analyze_data_for_errors(context, data: dict) -> dict[str, Any]:
    """Analyze data to identify potential issues."""
    r_script = get_r_script("helpers", "analyze_data_for_errors")
    try:
        analysis = await execute_r_script_async(r_script, {"data": data})
        return analysis
    except Exception:
        return {"issues": [], "suggestions": []}


@tool(
    name="validate_data",
    input_schema={
        "type": "object",
        "properties": {
            "data": {"type": "object", "description": "Dataset to validate"},
            "analysis_type": {
                "type": "string",
                "enum": [
                    "regression",
                    "correlation",
                    "timeseries",
                    "classification",
                    "general",
                ],
                "default": "general",
            },
            "strict": {
                "type": "boolean",
                "default": False,
                "description": "Enable strict validation with more checks",
            },
        },
        "required": ["data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "is_valid": {
                "type": "boolean",
                "description": "Whether the data passes validation",
            },
            "warnings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Validation warnings that don't prevent analysis",
            },
            "errors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Critical errors that prevent analysis",
            },
            "suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Suggestions for improving data quality",
            },
            "data_quality": {
                "type": "object",
                "properties": {
                    "dimensions": {
                        "type": "object",
                        "properties": {
                            "rows": {"type": "integer", "minimum": 0},
                            "columns": {"type": "integer", "minimum": 0},
                        },
                    },
                    "variable_types": {
                        "type": "object",
                        "properties": {
                            "numeric": {"type": "integer", "minimum": 0},
                            "character": {"type": "integer", "minimum": 0},
                            "factor": {"type": "integer", "minimum": 0},
                            "logical": {"type": "integer", "minimum": 0},
                        },
                    },
                    "missing_values": {
                        "type": "object",
                        "properties": {
                            "total_missing_cells": {"type": "integer", "minimum": 0},
                            "variables_with_missing": {"type": "integer", "minimum": 0},
                            "max_missing_percentage": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                            },
                        },
                    },
                    "data_issues": {
                        "type": "object",
                        "properties": {
                            "constant_variables": {"type": "integer", "minimum": 0},
                            "high_outlier_variables": {"type": "integer", "minimum": 0},
                            "duplicate_rows": {
                                "type": ["integer", "null"],
                                "minimum": 0,
                            },
                        },
                    },
                },
                "description": "Detailed data quality assessment",
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Analysis-specific recommendations",
            },
        },
        "required": [
            "is_valid",
            "warnings",
            "errors",
            "suggestions",
            "data_quality",
            "recommendations",
        ],
        "additionalProperties": False,
    },
    description="Performs comprehensive data quality validation checking for missing values, outliers, data type consistency, range validity, and structural issues that could cause analysis failures. Provides detailed quality reports with severity ratings and remediation suggestions. Use before statistical analyzes to prevent errors, ensure data reliability, meet analysis assumptions, or generate data quality documentation for research compliance.",
)
async def validate_data(context, params) -> dict[str, Any]:
    """Validate data for analysis and identify potential issues."""
    data = params["data"]
    analysis_type = params.get("analysis_type", "general")
    strict = params.get("strict", False)
    await context.info("Validating data", analysis_type=analysis_type)
    # Create R script with interpolated values
    r_script = get_r_script("helpers", "validate_data")
    # Pass the analysis type and strict mode as arguments
    params["analysis_type"] = analysis_type
    params["strict"] = strict
    try:
        result = await execute_r_script_async(r_script, {"data": data})
        # Add analysis-specific recommendations
        recommendations = _get_analysis_recommendations(analysis_type, result)
        result["recommendations"] = recommendations
        await context.info(
            "Data validation completed",
            is_valid=result["is_valid"],
            warnings_count=len(result["warnings"]),
            errors_count=len(result["errors"]),
        )
        return result
    except Exception as e:
        await context.error("Data validation failed", error=str(e))
        return {
            "is_valid": False,
            "errors": [f"Validation failed: {str(e)}"],
            "warnings": [],
            "suggestions": ["Check data format and try again"],
            "data_quality": {},
            "recommendations": [],
        }


def _get_analysis_recommendations(
    analysis_type: str, validation_result: dict
) -> list[str]:
    """Get analysis-specific recommendations based on validation results."""
    recommendations = []
    data_quality = validation_result.get("data_quality", {})
    if analysis_type == "regression":
        if data_quality.get("dimensions", {}).get("rows", 0) < 30:
            recommendations.append(
                "For reliable regression results, consider collecting more data (n >= 30)"
            )
        if data_quality.get("variable_types", {}).get("numeric", 0) < 2:
            recommendations.append(
                "Ensure you have numeric variables for regression analysis"
            )
    elif analysis_type == "correlation":
        if data_quality.get("variable_types", {}).get("numeric", 0) < 2:
            recommendations.append(
                "Correlation analysis requires at least 2 numeric variables"
            )
        if data_quality.get("missing_values", {}).get("max_missing_percentage", 0) > 20:
            recommendations.append(
                "High missing values may affect correlation estimates"
            )
    elif analysis_type == "timeseries":
        if data_quality.get("dimensions", {}).get("rows", 0) < 20:
            recommendations.append(
                "Time series analysis works better with more observations (n >= 20)"
            )
    # General recommendations
    if data_quality.get("data_issues", {}).get("constant_variables", 0) > 0:
        recommendations.append("Remove constant variables before analysis")
    if data_quality.get("missing_values", {}).get("max_missing_percentage", 0) > 30:
        recommendations.append(
            "Consider imputation or removal of variables with high missing values"
        )
    return recommendations


@tool(
    name="load_example",
    input_schema={
        "type": "object",
        "properties": {
            "dataset_name": {
                "type": "string",
                "enum": ["sales", "economics", "customers", "timeseries", "survey"],
                "description": "Name of example dataset",
            },
            "size": {
                "type": "string",
                "enum": ["small", "medium", "large"],
                "default": "small",
                "description": "Dataset size",
            },
            "add_noise": {
                "type": "boolean",
                "default": False,
                "description": "Add realistic noise/missing values",
            },
        },
        "required": ["dataset_name"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "description": "Example dataset in column-wise format",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": ["string", "number", "boolean", "null"]},
                },
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": [
                            "sales",
                            "economics",
                            "customers",
                            "timeseries",
                            "survey",
                        ],
                        "description": "Dataset name",
                    },
                    "description": {
                        "type": "string",
                        "description": "Dataset description and purpose",
                    },
                    "size": {
                        "type": "string",
                        "enum": ["small", "medium", "large"],
                        "description": "Size category of the dataset",
                    },
                    "rows": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Number of rows in the dataset",
                    },
                    "columns": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Number of columns in the dataset",
                    },
                    "has_noise": {
                        "type": "boolean",
                        "description": "Whether noise/missing values were added",
                    },
                },
                "description": "Dataset metadata and information",
            },
            "statistics": {
                "type": "object",
                "description": "Basic statistics for numeric variables",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "mean": {"type": "number"},
                        "sd": {"type": "number", "minimum": 0},
                        "min": {"type": "number"},
                        "max": {"type": "number"},
                        "missing": {"type": "integer", "minimum": 0},
                    },
                },
            },
            "suggested_analyses": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Suggested analyses appropriate for this dataset",
            },
            "variable_info": {
                "type": "object",
                "properties": {
                    "numeric_variables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of numeric variables",
                    },
                    "categorical_variables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of categorical variables",
                    },
                    "variable_types": {
                        "type": "object",
                        "description": "Data type for each variable",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "description": "Information about variables in the dataset",
            },
        },
        "required": [
            "data",
            "metadata",
            "statistics",
            "suggested_analyses",
            "variable_info",
        ],
        "additionalProperties": False,
    },
    description="Loads curated example datasets suitable for demonstrating statistical techniques, testing analysis workflows, or learning RMCP functionality. Includes classic datasets (iris, mtcars, economics) with documentation and suggested analyses. Use for tutorials, testing new analytical approaches, teaching statistical concepts, or exploring RMCP capabilities with known datasets that have well-understood properties and expected results.",
)
async def load_example(context, params) -> dict[str, Any]:
    """Load example datasets for analysis and testing."""
    dataset_name = params["dataset_name"]
    size = params.get("size", "small")
    await context.info("Loading example dataset", name=dataset_name, size=size)
    r_script = get_r_script("helpers", "load_example")
    try:
        result = await execute_r_script_async(r_script, params)
        await context.info(
            "Example dataset loaded successfully",
            rows=result["metadata"]["rows"],
            columns=result["metadata"]["columns"],
        )
        return result
    except Exception as e:
        await context.error("Failed to load example dataset", error=str(e))
        return {
            "error": f"Failed to load example dataset: {str(e)}",
            "data": {},
            "metadata": {
                "name": dataset_name,
                "rows": 0,
                "columns": 0,
                "description": "Failed to load",
            },
            "suggested_analyses": [],
        }
