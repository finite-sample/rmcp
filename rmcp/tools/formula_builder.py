"""
Formula Builder Tools for RMCP.
Natural language to R formula conversion and validation.
"""

import re
from typing import Any

from ..core.schemas import table_schema
from ..r_assets.loader import get_r_script
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="build_formula",
    input_schema={
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Natural language description of the relationship",
            },
            "data": {
                "type": "object",
                "description": "Optional data to validate variable names",
            },
            "analysis_type": {
                "type": "string",
                "enum": [
                    "regression",
                    "correlation",
                    "anova",
                    "classification",
                    "general",
                ],
                "default": "regression",
            },
            "suggest_alternatives": {"type": "boolean", "default": True},
        },
        "required": ["description"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "formula": {
                "type": ["string", "null"],
                "description": "Generated R formula",
            },
            "matched_pattern": {
                "type": ["string", "null"],
                "description": "Pattern that was matched to generate the formula",
            },
            "alternatives": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Alternative formula specifications",
            },
            "validation": {
                "type": ["object", "null"],
                "description": "Validation results if data was provided",
                "properties": {
                    "is_valid": {"type": "boolean"},
                    "missing_variables": {"type": "array", "items": {"type": "string"}},
                    "existing_variables": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "available_variables": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "variable_types": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "warnings": {"type": "array", "items": {"type": "string"}},
                    "formula_parsed": {"type": "boolean"},
                    "error": {"type": "string"},
                },
            },
            "examples": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "formula": {"type": "string"},
                        "use_case": {"type": "string"},
                    },
                },
                "description": "Example formulas for the analysis type",
            },
            "interpretation": {
                "type": ["string", "null"],
                "description": "Human-readable interpretation of the formula",
            },
            "suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Suggestions for improving the formula",
            },
        },
        "required": [
            "formula",
            "matched_pattern",
            "alternatives",
            "examples",
            "interpretation",
            "suggestions",
        ],
        "additionalProperties": False,
    },
    description="Converts natural language descriptions into proper R statistical formulas using intelligent pattern matching and variable name recognition. Handles complex relationships including interactions, transformations, and nested terms. Validates variable names against provided datasets and suggests corrections for typos. Use when users describe statistical relationships in plain English rather than formal formula syntax, or to help non-technical users specify models correctly.",
)
async def build_formula(context, params) -> dict[str, Any]:
    """Convert natural language to R formula."""
    description = params["description"].lower()
    analysis_type = params.get("analysis_type", "regression")
    data = params.get("data")
    suggest_alternatives = params.get("suggest_alternatives", True)
    await context.info("Building formula from description", description=description)
    # Define pattern mappings for natural language to formula conversion
    patterns = [
        # Basic prediction patterns
        (r"predict\s+(\w+)\s+from\s+(.*)", r"\1 ~ \2"),
        (r"(\w+)\s+depends\s+on\s+(.*)", r"\1 ~ \2"),
        (r"(\w+)\s+as\s+function\s+of\s+(.*)", r"\1 ~ \2"),
        (r"(\w+)\s+explained\s+by\s+(.*)", r"\1 ~ \2"),
        (r"(\w+)\s+caused\s+by\s+(.*)", r"\1 ~ \2"),
        (r"(\w+)\s+influenced\s+by\s+(.*)", r"\1 ~ \2"),
        # Comparison patterns
        (r"(\w+)\s+by\s+(\w+)", r"\1 ~ \2"),
        (r"(\w+)\s+across\s+(\w+)", r"\1 ~ \2"),
        (r"(\w+)\s+between\s+(\w+)", r"\1 ~ \2"),
        # Time series patterns
        (r"(\w+)\s+over\s+time", r"\1 ~ time"),
        (r"(\w+)\s+through\s+time", r"\1 ~ time"),
        (r"(\w+)\s+trend", r"\1 ~ time"),
        # Control patterns
        (r"(\w+)\s+controlling\s+for\s+(.*)", r"\1 ~ . + \2"),
        (r"(\w+)\s+adjusting\s+for\s+(.*)", r"\1 ~ . + \2"),
        # Interaction patterns
        (r"interaction\s+between\s+(\w+)\s+and\s+(\w+)", r"\1 * \2"),
        (r"(\w+)\s+and\s+(\w+)\s+interaction", r"\1 * \2"),
        (r"(\w+)\s+interacts\s+with\s+(\w+)", r"\1 * \2"),
        # Multiple variables
        (r"(\w+)\s+from\s+(\w+)\s+and\s+(.*)", r"\1 ~ \2 + \3"),
        (r"(\w+)\s+using\s+(\w+)\s+and\s+(.*)", r"\1 ~ \2 + \3"),
    ]
    # Apply pattern matching
    formula = None
    matched_pattern = None
    for pattern, replacement in patterns:
        match = re.search(pattern, description)
        if match:
            formula = re.sub(pattern, replacement, description)
            matched_pattern = pattern
            break
    # Clean up formula
    if formula:
        # Replace common words with R operators
        formula = re.sub(r"\s+and\s+", " + ", formula)
        formula = re.sub(r"\s+plus\s+", " + ", formula)
        formula = re.sub(r"\s+with\s+", " + ", formula)
        formula = re.sub(r"\s+including\s+", " + ", formula)
        formula = re.sub(r"\s+,\s+", " + ", formula)
        # Clean whitespace
        formula = re.sub(r"\s+", " ", formula).strip()
    # If no pattern matched, try to extract variables manually
    if not formula:
        words = description.split()
        potential_vars = [w for w in words if w.isalnum() and len(w) > 1]
        if len(potential_vars) >= 2:
            # Assume first is outcome, rest are predictors
            outcome = potential_vars[0]
            predictors = " + ".join(potential_vars[1:])
            formula = f"{outcome} ~ {predictors}"
            matched_pattern = "manual extraction"
    # Generate alternative formulas if requested
    alternatives = []
    if suggest_alternatives and formula:
        alternatives = _generate_formula_alternatives(formula, analysis_type)
    # Validate formula syntax if data is provided
    validation_result = None
    if formula and data:
        validation_result = await _validate_formula(context, formula, data)
    # Create examples based on analysis type
    examples = _get_formula_examples(analysis_type)
    result = {
        "formula": formula,
        "matched_pattern": matched_pattern,
        "alternatives": alternatives,
        "validation": validation_result,
        "examples": examples,
        "interpretation": _interpret_formula(formula) if formula else None,
        "suggestions": _get_improvement_suggestions(description, formula or ""),
    }
    await context.info("Formula built successfully", formula=formula)
    return result


def _generate_formula_alternatives(base_formula: str, analysis_type: str) -> list[str]:
    """Generate alternative formula specifications."""
    alternatives: list[str] = []
    if "~" not in base_formula:
        return alternatives
    outcome, predictors = base_formula.split("~", 1)
    outcome = outcome.strip()
    predictors = predictors.strip()
    # Basic alternatives
    alternatives.append(f"{outcome} ~ {predictors}")  # Original
    # Add interaction terms
    if "+" in predictors and "*" not in predictors:
        pred_list = [p.strip() for p in predictors.split("+")]
        if len(pred_list) == 2:
            alternatives.append(f"{outcome} ~ {pred_list[0]} * {pred_list[1]}")
        elif len(pred_list) > 2:
            alternatives.append(
                f"{outcome} ~ ({predictors}) + {pred_list[0]} * {pred_list[1]}"
            )
    # Add polynomial terms
    if "+" in predictors:
        pred_list = [p.strip() for p in predictors.split("+")]
        for pred in pred_list[:2]:  # Only first two to avoid complexity
            alternatives.append(f"{outcome} ~ {predictors} + I({pred}^2)")
    # Add all variables option
    alternatives.append(f"{outcome} ~ .")
    # Add intercept removal option
    alternatives.append(f"{outcome} ~ {predictors} - 1")
    return list(set(alternatives))  # Remove duplicates


async def _validate_formula(context, formula: str, data: dict) -> dict[str, Any]:
    """Validate formula against provided data."""
    r_script = get_r_script("formula_builder", "validate_formula")
    try:
        validation = await execute_r_script_async(
            r_script, {"data": data, "formula": formula}
        )
        return validation
    except Exception as e:
        return {"is_valid": False, "error": str(e), "formula_parsed": False}


def _interpret_formula(formula: str) -> str:
    """Provide interpretation of the formula."""
    if not formula or "~" not in formula:
        return "Invalid formula format"
    outcome, predictors = formula.split("~", 1)
    outcome = outcome.strip()
    predictors = predictors.strip()
    interpretation = f"This formula models '{outcome}' as the outcome variable"
    if predictors == ".":
        interpretation += " using all other variables in the dataset as predictors."
    elif "+" in predictors:
        pred_list = [p.strip() for p in predictors.split("+")]
        interpretation += (
            f" with {len(pred_list)} predictor variables: {', '.join(pred_list[:3])}"
        )
        if len(pred_list) > 3:
            interpretation += f" and {len(pred_list) - 3} others"
        interpretation += "."
    elif "*" in predictors:
        interpretation += f" including interaction effects between {predictors.replace('*', ' and ')}."
    else:
        interpretation += f" with '{predictors}' as the predictor variable."
    # Add notes about special terms
    if "I(" in formula:
        interpretation += " The formula includes polynomial or transformation terms."
    if "- 1" in formula:
        interpretation += " The intercept term is excluded from the model."
    return interpretation


def _get_improvement_suggestions(description: str, formula: str) -> list[str]:
    """Generate suggestions for improving the formula."""
    suggestions = []
    if not formula:
        suggestions.append(
            "Try rephrasing with clearer variable relationships (e.g., 'predict Y from X')"
        )
        suggestions.append(
            "Specify the outcome variable and predictor variables explicitly"
        )
        return suggestions
    # Check for common improvements
    if "+" not in formula and "*" not in formula and "~" in formula:
        suggestions.append(
            "Consider adding interaction terms with * operator (e.g., 'x1 * x2')"
        )
    if "time" in description.lower() and "time" not in formula.lower():
        suggestions.append("For time series data, consider adding time trends or lags")
    if any(word in description.lower() for word in ["control", "adjust", "account"]):
        suggestions.append("Use '. +' to include all variables plus specific controls")
    if "squared" in description.lower() or "quadratic" in description.lower():
        suggestions.append(
            "Add polynomial terms with I(variable^2) for curved relationships"
        )
    return suggestions


def _get_formula_examples(analysis_type: str) -> list[dict[str, str]]:
    """Get example formulas for different analysis types."""
    examples = {
        "regression": [
            {
                "description": "Simple regression",
                "formula": "y ~ x",
                "use_case": "One predictor variable",
            },
            {
                "description": "Multiple regression",
                "formula": "y ~ x1 + x2 + x3",
                "use_case": "Multiple predictors",
            },
            {
                "description": "Interaction model",
                "formula": "y ~ x1 * x2",
                "use_case": "Variables interact with each other",
            },
            {
                "description": "Polynomial regression",
                "formula": "y ~ x + I(x^2)",
                "use_case": "Curved relationships",
            },
            {
                "description": "All variables",
                "formula": "y ~ .",
                "use_case": "Use all available predictors",
            },
        ],
        "anova": [
            {
                "description": "One-way ANOVA",
                "formula": "y ~ group",
                "use_case": "Compare groups",
            },
            {
                "description": "Two-way ANOVA",
                "formula": "y ~ factor1 + factor2",
                "use_case": "Two categorical predictors",
            },
            {
                "description": "Interaction ANOVA",
                "formula": "y ~ factor1 * factor2",
                "use_case": "Factors interact",
            },
            {
                "description": "ANCOVA",
                "formula": "y ~ group + covariate",
                "use_case": "Groups with continuous control",
            },
        ],
        "correlation": [
            {
                "description": "Simple correlation",
                "formula": "~ x + y",
                "use_case": "Relationship between two variables",
            },
            {
                "description": "Multiple correlations",
                "formula": "~ x1 + x2 + x3",
                "use_case": "Correlation matrix",
            },
        ],
        "general": [
            {
                "description": "Basic relationship",
                "formula": "outcome ~ predictor",
                "use_case": "Most common format",
            },
            {
                "description": "Multiple predictors",
                "formula": "y ~ x1 + x2",
                "use_case": "Several variables",
            },
            {
                "description": "No intercept",
                "formula": "y ~ x - 1",
                "use_case": "Force through origin",
            },
            {
                "description": "All variables",
                "formula": "y ~ .",
                "use_case": "Use everything available",
            },
        ],
    }
    return examples.get(analysis_type, examples["general"])


@tool(
    name="validate_formula",
    input_schema={
        "type": "object",
        "properties": {
            "formula": {"type": "string", "description": "R formula to validate"},
            "data": table_schema(),
            "analysis_type": {
                "type": "string",
                "enum": ["regression", "anova", "correlation"],
                "default": "regression",
            },
        },
        "required": ["formula", "data"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "is_valid": {
                "type": "boolean",
                "description": "Whether the formula is valid",
            },
            "missing_variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables in formula but not in data",
            },
            "existing_variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables in formula that exist in data",
            },
            "available_variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "All variables available in the dataset",
            },
            "variable_types": {
                "type": "object",
                "description": "Data types of variables in the formula",
                "additionalProperties": {"type": "string"},
            },
            "warnings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Validation warnings about data quality or types",
            },
            "formula_parsed": {
                "type": "boolean",
                "description": "Whether the formula syntax is valid",
            },
            "error": {
                "type": "string",
                "description": "Error message if validation failed",
            },
            "suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Suggestions for fixing or improving the formula",
            },
            "analysis_type": {
                "type": "string",
                "enum": ["regression", "anova", "correlation"],
                "description": "Type of analysis the formula is intended for",
            },
        },
        "required": ["is_valid", "formula_parsed", "suggestions", "analysis_type"],
        "additionalProperties": False,
    },
    description="Validates R formula syntax and checks compatibility with provided datasets including variable existence, data type appropriateness, and formula structure correctness. Identifies missing variables, type mismatches, and syntax errors with specific suggestions for fixes. Essential quality control before running statistical analyzes. Use to catch formula errors early, ensure model specifications are valid, or verify that formulas match intended analytical objectives.",
)
async def validate_formula(context, params) -> dict[str, Any]:
    """Validate R formula against data."""
    formula = params["formula"]
    data = params["data"]
    analysis_type = params.get("analysis_type", "regression")
    await context.info("Validating formula", formula=formula)
    # Basic syntax validation
    if "~" not in formula:
        return {
            "is_valid": False,
            "error": "Formula must contain '~' separator",
            "suggestions": ["Use format: outcome ~ predictor1 + predictor2"],
        }
    # Detailed validation using R
    validation = await _validate_formula(context, formula, data)
    # Add suggestions based on validation results
    suggestions = []
    if not validation.get("is_valid", False):
        if validation.get("missing_variables"):
            suggestions.append(
                f"Missing variables: {', '.join(validation['missing_variables'])}"
            )
            if validation.get("available_variables"):
                suggestions.append(
                    f"Available variables: {', '.join(validation['available_variables'][:10])}"
                )
    if validation.get("warnings"):
        suggestions.extend(validation["warnings"])
    # Add analysis-specific suggestions
    if analysis_type == "anova" and validation.get("variable_types"):
        numeric_predictors = [
            var
            for var, vtype in validation["variable_types"].items()
            if vtype in ["numeric", "integer"]
        ]
        if numeric_predictors:
            suggestions.append(
                f"For ANOVA, consider converting numeric predictors to factors: {', '.join(numeric_predictors)}"
            )
    validation["suggestions"] = suggestions
    validation["analysis_type"] = analysis_type
    return validation
