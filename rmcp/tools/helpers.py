"""
Error Recovery and Helper Tools for RMCP.

Intelligent error diagnosis, data validation, and recovery suggestions.
"""

import re
from typing import Any

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
    description="Analyze errors and suggest fixes with actionable solutions",
)
async def suggest_fix(context, params) -> dict[str, Any]:
    """Analyze error and provide actionable solutions."""

    error_message = params["error_message"]
    tool_name = params.get("tool_name", "unknown")
    data = params.get("data")
    parameters = params.get("parameters")

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
                "Install all RMCP packages at once with the command in the documentation",
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
        except:
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

    r_script = """
    data <- as.data.frame(args$data)
    
    # Basic data analysis
    n_rows <- nrow(data)
    n_cols <- ncol(data)
    col_names <- names(data)
    
    # Check for potential issues
    issues <- c()
    suggestions <- c()
    
    # Missing values
    missing_counts <- sapply(data, function(x) sum(is.na(x)))
    high_missing <- names(missing_counts[missing_counts > 0.1 * n_rows])
    
    if (length(high_missing) > 0) {
        issues <- c(issues, "High missing values detected")
        suggestions <- c(suggestions, paste("High missing values in:", paste(high_missing, collapse=", ")))
    }
    
    # Variable types
    var_types <- sapply(data, class)
    char_vars <- names(var_types[var_types == "character"])
    
    if (length(char_vars) > 0) {
        suggestions <- c(suggestions, paste("Character variables may need conversion:", paste(char_vars, collapse=", ")))
    }
    
    # Small sample size
    if (n_rows < 10) {
        issues <- c(issues, "Small sample size")
        suggestions <- c(suggestions, "Sample size is small - results may be unreliable")
    }
    
    # Single column
    if (n_cols == 1) {
        issues <- c(issues, "Single variable")
        suggestions <- c(suggestions, "Only one variable - cannot perform relationship analysis")
    }
    
    # Constant variables
    constant_vars <- names(data)[sapply(data, function(x) length(unique(x[!is.na(x)])) <= 1)]
    if (length(constant_vars) > 0) {
        issues <- c(issues, "Constant variables detected")
        suggestions <- c(suggestions, paste("Constant variables (no variation):", paste(constant_vars, collapse=", ")))
    }
    
    result <- list(
        issues = issues,
        suggestions = suggestions,
        data_summary = list(
            rows = n_rows,
            columns = n_cols,
            missing_values = as.list(missing_counts),
            variable_types = as.list(var_types)
        )
    )
    """

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
    description="Validate data quality and identify potential issues before analysis",
)
async def validate_data(context, params) -> dict[str, Any]:
    """Validate data for analysis and identify potential issues."""

    data = params["data"]
    analysis_type = params.get("analysis_type", "general")
    strict = params.get("strict", False)

    await context.info("Validating data", analysis_type=analysis_type)

    r_script = f"""
    library(dplyr)
    
    data <- as.data.frame(args$data)
    analysis_type <- "{analysis_type}"
    strict_mode <- {"TRUE" if strict else "FALSE"}
    
    # Basic validation
    n_rows <- nrow(data)
    n_cols <- ncol(data)
    col_names <- names(data)
    
    # Initialize results
    validation_results <- list(
        is_valid = TRUE,
        warnings = c(),
        errors = c(),
        suggestions = c(),
        data_quality = list()
    )
    
    # Check basic requirements
    if (n_rows == 0) {{
        validation_results$is_valid <- FALSE
        validation_results$errors <- c(validation_results$errors, "Dataset is empty (no rows)")
    }}
    
    if (n_cols == 0) {{
        validation_results$is_valid <- FALSE
        validation_results$errors <- c(validation_results$errors, "Dataset has no columns")
    }}
    
    # Missing value analysis
    missing_counts <- sapply(data, function(x) sum(is.na(x)))
    missing_percentages <- missing_counts / n_rows * 100
    high_missing <- names(missing_percentages[missing_percentages > 50])
    
    if (length(high_missing) > 0) {{
        validation_results$warnings <- c(validation_results$warnings, 
                                        paste("High missing values (>50%) in:", paste(high_missing, collapse=", ")))
    }}
    
    # Variable type analysis
    var_types <- sapply(data, class)
    numeric_vars <- names(var_types[var_types %in% c("numeric", "integer")])
    character_vars <- names(var_types[var_types == "character"])
    factor_vars <- names(var_types[var_types == "factor"])
    logical_vars <- names(var_types[var_types == "logical"])
    
    # Analysis-specific validation
    if (analysis_type == "regression") {{
        if (n_cols < 2) {{
            validation_results$errors <- c(validation_results$errors, "Regression requires at least 2 variables (outcome + predictor)")
        }}
        
        if (n_rows < 10) {{
            validation_results$warnings <- c(validation_results$warnings, "Small sample size for regression (n < 10)")
        }}
        
        if (length(numeric_vars) == 0) {{
            validation_results$warnings <- c(validation_results$warnings, "No numeric variables found - may need conversion")
        }}
    }}
    
    if (analysis_type == "correlation") {{
        if (length(numeric_vars) < 2) {{
            validation_results$errors <- c(validation_results$errors, "Correlation requires at least 2 numeric variables")
        }}
        
        if (n_rows < 3) {{
            validation_results$errors <- c(validation_results$errors, "Correlation requires at least 3 observations")
        }}
    }}
    
    if (analysis_type == "timeseries") {{
        if (n_rows < 10) {{
            validation_results$warnings <- c(validation_results$warnings, "Small sample size for time series (n < 10)")
        }}
        
        if (length(numeric_vars) == 0) {{
            validation_results$errors <- c(validation_results$errors, "Time series analysis requires numeric variables")
        }}
    }}
    
    if (analysis_type == "classification") {{
        # Look for binary/categorical variables
        binary_vars <- names(data)[sapply(data, function(x) length(unique(x[!is.na(x)])) == 2)]
        
        if (length(binary_vars) == 0 && length(factor_vars) == 0) {{
            validation_results$warnings <- c(validation_results$warnings, "No obvious outcome variable for classification found")
        }}
    }}
    
    # Data quality checks
    
    # Constant variables
    constant_vars <- names(data)[sapply(data, function(x) length(unique(x[!is.na(x)])) <= 1)]
    if (length(constant_vars) > 0) {{
        validation_results$warnings <- c(validation_results$warnings, 
                                        paste("Constant variables (no variation):", paste(constant_vars, collapse=", ")))
    }}
    
    # Outliers (for numeric variables)
    outlier_info <- list()
    for (var in numeric_vars) {{
        if (sum(!is.na(data[[var]])) > 0) {{
            Q1 <- quantile(data[[var]], 0.25, na.rm = TRUE)
            Q3 <- quantile(data[[var]], 0.75, na.rm = TRUE)
            IQR <- Q3 - Q1
            outliers <- sum(data[[var]] < (Q1 - 1.5 * IQR) | data[[var]] > (Q3 + 1.5 * IQR), na.rm = TRUE)
            outlier_percentage <- outliers / sum(!is.na(data[[var]])) * 100
            
            if (outlier_percentage > 10) {{
                outlier_info[[var]] <- outlier_percentage
            }}
        }}
    }}
    
    if (length(outlier_info) > 0) {{
        validation_results$warnings <- c(validation_results$warnings, 
                                        paste("High outlier percentage in:", paste(names(outlier_info), collapse=", ")))
    }}
    
    # Strict mode additional checks
    if (strict_mode) {{
        # Check for duplicate rows
        duplicate_rows <- sum(duplicated(data))
        if (duplicate_rows > 0) {{
            validation_results$warnings <- c(validation_results$warnings, 
                                            paste("Duplicate rows found:", duplicate_rows))
        }}
        
        # Check variable name issues
        problematic_names <- col_names[grepl("[^a-zA-Z0-9_.]", col_names)]
        if (length(problematic_names) > 0) {{
            validation_results$warnings <- c(validation_results$warnings, 
                                            paste("Variable names with special characters:", paste(problematic_names, collapse=", ")))
        }}
        
        # Check for very wide data
        if (n_cols > n_rows && n_rows < 100) {{
            validation_results$warnings <- c(validation_results$warnings, 
                                            "More variables than observations - may be problematic")
        }}
    }}
    
    # Generate suggestions
    suggestions <- c()
    
    if (length(character_vars) > 0) {{
        suggestions <- c(suggestions, paste("Consider converting character variables to factors:", paste(character_vars[1:min(3, length(character_vars))], collapse=", ")))
    }}
    
    if (any(missing_percentages > 10)) {{
        suggestions <- c(suggestions, "Consider handling missing values before analysis")
    }}
    
    if (length(constant_vars) > 0) {{
        suggestions <- c(suggestions, "Remove constant variables as they don't contribute to analysis")
    }}
    
    if (n_rows < 30) {{
        suggestions <- c(suggestions, "Small sample size - interpret results cautiously")
    }}
    
    validation_results$suggestions <- suggestions
    
    # Data quality summary
    validation_results$data_quality <- list(
        dimensions = list(rows = n_rows, columns = n_cols),
        variable_types = list(
            numeric = length(numeric_vars),
            character = length(character_vars),
            factor = length(factor_vars),
            logical = length(logical_vars)
        ),
        missing_values = list(
            total_missing_cells = sum(missing_counts),
            variables_with_missing = sum(missing_counts > 0),
            max_missing_percentage = if(length(missing_percentages) > 0) max(missing_percentages) else 0
        ),
        data_issues = list(
            constant_variables = length(constant_vars),
            high_outlier_variables = length(outlier_info),
            duplicate_rows = if(strict_mode) duplicate_rows else NA
        )
    )
    
    # Ensure arrays are properly formatted for JSON
    validation_results$warnings <- if(length(validation_results$warnings) == 0) character(0) else validation_results$warnings
    validation_results$errors <- if(length(validation_results$errors) == 0) character(0) else validation_results$errors
    validation_results$suggestions <- if(length(validation_results$suggestions) == 0) character(0) else validation_results$suggestions
    
    result <- validation_results
    """

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
    description="Load example datasets for testing and learning",
)
async def load_example(context, params) -> dict[str, Any]:
    """Load example datasets for analysis and testing."""

    dataset_name = params["dataset_name"]
    size = params.get("size", "small")
    add_noise = params.get("add_noise", False)

    await context.info("Loading example dataset", name=dataset_name, size=size)

    r_script = f"""
    library(dplyr)
    
    dataset_name <- "{dataset_name}"
    size_param <- "{size}"
    add_noise <- {"TRUE" if add_noise else "FALSE"}
    
    # Set size parameters
    size_map <- list(
        small = 20,
        medium = 100,
        large = 500
    )
    n <- size_map[[size_param]]
    
    set.seed(42)  # For reproducible examples
    
    if (dataset_name == "sales") {{
        # Sales and marketing data
        months <- 1:n
        marketing_spend <- round(rnorm(n, 1000, 200), 0)
        sales <- round(50 + 4.5 * marketing_spend + rnorm(n, 0, 500), 0)
        
        # Add some seasonal effect
        seasonal <- 200 * sin(2 * pi * months / 12)
        sales <- sales + seasonal
        
        data <- data.frame(
            month = months,
            marketing_spend = pmax(marketing_spend, 0),
            sales = pmax(sales, 0),
            quarter = paste0("Q", ceiling(months %% 12 / 3))
        )
        
        description <- "Sales and marketing spend data with seasonal patterns"
        
    }} else if (dataset_name == "economics") {{
        # Economic indicators
        years <- seq(2000, 2000 + n/4, length.out = n)
        gdp_growth <- round(rnorm(n, 2.5, 1.2), 2)
        unemployment <- round(8 - 0.8 * gdp_growth + rnorm(n, 0, 0.5), 1)
        investment <- round(18 + 0.3 * gdp_growth + rnorm(n, 0, 2), 1)
        
        data <- data.frame(
            year = years,
            gdp_growth = gdp_growth,
            unemployment = pmax(unemployment, 1),
            investment = pmax(investment, 10),
            country = sample(c("USA", "GBR", "DEU", "FRA"), n, replace = TRUE)
        )
        
        description <- "Economic indicators demonstrating Okun's Law and investment relationships"
        
    }} else if (dataset_name == "customers") {{
        # Customer data for churn analysis
        customer_id <- 1:n
        tenure_months <- sample(1:72, n, replace = TRUE)
        monthly_charges <- round(runif(n, 20, 120), 2)
        total_charges <- round(tenure_months * monthly_charges + rnorm(n, 0, 100), 2)
        
        # Churn probability based on tenure and charges
        churn_prob <- plogis(-2 + -0.05 * tenure_months + 0.02 * monthly_charges)
        churned <- rbinom(n, 1, churn_prob)
        
        age <- sample(18:80, n, replace = TRUE)
        
        data <- data.frame(
            customer_id = customer_id,
            age = age,
            tenure_months = tenure_months,
            monthly_charges = monthly_charges,
            total_charges = pmax(total_charges, 0),
            churned = churned,
            contract_type = sample(c("Month-to-month", "One year", "Two year"), n, replace = TRUE, prob = c(0.5, 0.3, 0.2))
        )
        
        description <- "Customer data for churn prediction analysis"
        
    }} else if (dataset_name == "timeseries") {{
        # Time series data with trend and seasonality
        time_points <- 1:n
        trend <- 0.5 * time_points
        seasonal <- 10 * sin(2 * pi * time_points / 12) + 5 * cos(2 * pi * time_points / 4)
        noise <- rnorm(n, 0, 3)
        
        value <- 100 + trend + seasonal + noise
        
        data <- data.frame(
            time = time_points,
            value = round(value, 2),
            month = rep(1:12, length.out = n),
            year = rep(2020:(2020 + ceiling(n/12)), each = 12)[1:n]
        )
        
        description <- "Time series data with trend and seasonal components"
        
    }} else if (dataset_name == "survey") {{
        # Survey data with Likert scales
        respondent_id <- 1:n
        age <- sample(18:75, n, replace = TRUE)
        satisfaction <- sample(1:10, n, replace = TRUE, prob = c(0.05, 0.05, 0.1, 0.1, 0.15, 0.15, 0.15, 0.15, 0.05, 0.05))
        
        # Purchase frequency correlated with satisfaction
        purchase_freq <- pmax(1, round(satisfaction * 0.8 + rnorm(n, 0, 1.5)), 0)
        
        education <- sample(c("High School", "Bachelor", "Master", "PhD"), n, replace = TRUE, prob = c(0.3, 0.4, 0.25, 0.05))
        income_bracket <- sample(c("< $30k", "$30-50k", "$50-75k", "$75-100k", "> $100k"), n, replace = TRUE, prob = c(0.2, 0.25, 0.25, 0.2, 0.1))
        
        data <- data.frame(
            respondent_id = respondent_id,
            age = age,
            satisfaction = satisfaction,
            purchase_frequency = purchase_freq,
            education = education,
            income_bracket = income_bracket
        )
        
        description <- "Survey data with satisfaction and demographic variables"
        
    }} else {{
        stop("Unknown dataset name")
    }}
    
    # Add noise if requested
    if (add_noise) {{
        # Add missing values randomly (5-10% missing)
        missing_rate <- runif(1, 0.05, 0.10)
        for (col in names(data)) {{
            if (is.numeric(data[[col]])) {{
                missing_indices <- sample(1:nrow(data), round(nrow(data) * missing_rate))
                data[missing_indices, col] <- NA
            }}
        }}
        
        # Add some outliers to numeric columns
        numeric_cols <- names(data)[sapply(data, is.numeric)]
        for (col in numeric_cols) {{
            if (!all(is.na(data[[col]]))) {{
                # Add 2-3 outliers
                outlier_indices <- sample(which(!is.na(data[[col]])), min(3, sum(!is.na(data[[col]]))))
                mean_val <- mean(data[[col]], na.rm = TRUE)
                sd_val <- sd(data[[col]], na.rm = TRUE)
                data[outlier_indices, col] <- data[outlier_indices, col] + sample(c(-1, 1), length(outlier_indices), replace = TRUE) * 3 * sd_val
            }}
        }}
    }}
    
    # Calculate basic statistics
    numeric_vars <- names(data)[sapply(data, is.numeric)]
    stats <- list()
    for (var in numeric_vars) {{
        if (sum(!is.na(data[[var]])) > 0) {{
            stats[[var]] <- list(
                mean = round(mean(data[[var]], na.rm = TRUE), 2),
                sd = round(sd(data[[var]], na.rm = TRUE), 2),
                min = min(data[[var]], na.rm = TRUE),
                max = max(data[[var]], na.rm = TRUE),
                missing = sum(is.na(data[[var]]))
            )
        }}
    }}
    
    result <- list(
        data = as.list(data),  # Convert to column-wise format for schema compatibility
        metadata = list(
            name = dataset_name,
            description = description,
            size = size_param,
            rows = nrow(data),
            columns = ncol(data),
            has_noise = add_noise
        ),
        statistics = stats,
        suggested_analyses = list(),
        variable_info = list(
            numeric_variables = numeric_vars,
            categorical_variables = as.list(names(data)[sapply(data, function(x) is.factor(x) || is.character(x))]),
            variable_types = as.list(setNames(sapply(data, class), names(data)))
        )
    )
    
    # Add suggested analyses based on dataset
    if (dataset_name == "sales") {{
        result$suggested_analyses <- c(
            "Linear regression: sales ~ marketing_spend",
            "Correlation analysis between all numeric variables",
            "Time series analysis of sales data"
        )
    }} else if (dataset_name == "economics") {{
        result$suggested_analyses <- c(
            "Test Okun's Law: unemployment ~ gdp_growth",
            "Investment effects: gdp_growth ~ investment",
            "Panel regression with country effects"
        )
    }} else if (dataset_name == "customers") {{
        result$suggested_analyses <- c(
            "Logistic regression: churned ~ tenure_months + monthly_charges",
            "Survival analysis for customer retention",
            "Customer segmentation with clustering"
        )
    }} else if (dataset_name == "timeseries") {{
        result$suggested_analyses <- c(
            "ARIMA modeling and forecasting",
            "Time series decomposition",
            "Seasonal trend analysis"
        )
    }} else if (dataset_name == "survey") {{
        result$suggested_analyses <- c(
            "Correlation: satisfaction ~ purchase_frequency",
            "ANOVA: satisfaction by education level",
            "Multiple regression with demographic controls"
        )
    }}
    
    result
    """

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
