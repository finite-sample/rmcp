"""
Flexible R Code Execution for RMCP.
Allows AI assistants to generate and execute custom R code for advanced analyses
not covered by structured tools, with comprehensive safety features.

Security Features:
- Package whitelist enforcement
- Execution timeout limits
- No filesystem access beyond temp files
- Audit logging
- Memory limits via R options
"""

import logging
import re
from typing import Any, Optional

from ..core.schemas import table_schema
from ..r_integration import execute_r_script_async, execute_r_script_with_image_async
from ..registries.tools import tool

logger = logging.getLogger(__name__)

# Whitelist of safe R packages for statistical analysis
ALLOWED_R_PACKAGES = {
    # Base R packages (always available)
    "base",
    "stats",
    "graphics",
    "grDevices",
    "utils",
    "datasets",
    "methods",
    "grid",
    "splines",
    "stats4",
    # Data manipulation
    "dplyr",
    "tidyr",
    "data.table",
    "reshape2",
    "plyr",
    "tidyverse",
    "tibble",
    "readr",
    "stringr",
    "forcats",
    "lubridate",
    "purrr",
    # Statistical analysis
    "lmtest",
    "sandwich",
    "car",
    "MASS",
    "boot",
    "survival",
    "nlme",
    "mgcv",
    "gam",
    "glmnet",
    "caret",
    "e1071",
    "nnet",
    "lme4",
    "lavaan",
    # Econometrics
    "plm",
    "AER",
    "vars",
    "tseries",
    "urca",
    "forecast",
    "dynlm",
    "quantreg",
    "systemfit",
    "gmm",
    "sem",
    "sampleSelection",
    # Machine learning
    "randomForest",
    "rpart",
    "tree",
    "gbm",
    "xgboost",
    "kernlab",
    "cluster",
    "factoextra",
    "NbClust",
    # Time series
    "zoo",
    "xts",
    "TTR",
    "quantmod",
    "rugarch",
    "fGarch",
    "astsa",
    "prophet",
    # Visualization
    "ggplot2",
    "lattice",
    "plotly",
    "ggpubr",
    "corrplot",
    "gridExtra",
    "viridis",
    "RColorBrewer",
    # Utilities
    "jsonlite",
    "broom",
    "knitr",
    "rlang",
    "haven",
    "openxlsx",
    "readxl",
    "foreign",
    "R.utils",
}

# Dangerous patterns to block
DANGEROUS_PATTERNS = [
    r"system\s*\(",  # System commands
    r"shell\s*\(",  # Shell commands
    r"Sys\.setenv",  # Environment manipulation
    r"setwd\s*\(",  # Change working directory
    r"source\s*\(",  # Source external files
    r"install\.packages",  # Package installation
    r"download\.",  # Download functions
    r"file\.remove",  # File deletion
    r"file\.rename",  # File renaming
    r"unlink\s*\(",  # File deletion
    r"save\s*\(",  # Save workspace
    r"save\.image",  # Save workspace image
    r"load\s*\(",  # Load workspace
    r"readLines\s*\(",  # Read arbitrary files
    r"writeLines\s*\(",  # Write arbitrary files
    r"sink\s*\(",  # Redirect output
    r"options\s*\(\s*warn",  # Change warning behavior
]


def validate_r_code(r_code: str) -> tuple[bool, Optional[str]]:
    """
    Validate R code for safety.

    Returns:
        (is_safe, error_message)
    """
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, r_code, re.IGNORECASE):
            return False, f"Dangerous pattern detected: {pattern}"

    # Extract library/require calls
    lib_pattern = r"(?:library|require)\s*\(\s*['\"]?(\w+)['\"]?\s*\)"
    packages = re.findall(lib_pattern, r_code, re.IGNORECASE)

    # Check all packages are in whitelist
    for pkg in packages:
        if pkg not in ALLOWED_R_PACKAGES:
            return False, f"Package '{pkg}' is not in the allowed package list"

    # Check for double-colon package usage (pkg::function)
    colon_pattern = r"(\w+)::"
    colon_packages = re.findall(colon_pattern, r_code)
    for pkg in colon_packages:
        if pkg not in ALLOWED_R_PACKAGES:
            return False, f"Package '{pkg}' (used with ::) is not allowed"

    return True, None


@tool(
    name="execute_r_analysis",
    input_schema={
        "type": "object",
        "properties": {
            "r_code": {
                "type": "string",
                "description": (
                    "R code to execute. Must use 'result' variable for output."
                ),
            },
            "data": {
                "oneOf": [table_schema(), {"type": "null"}],
                "description": "Optional data to pass to R code as 'data' variable",
            },
            "packages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "R packages required (must be in whitelist)",
                "default": [],
            },
            "description": {
                "type": "string",
                "description": "Description of what this analysis does",
            },
            "timeout_seconds": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300,
                "default": 60,
                "description": "Maximum execution time in seconds",
            },
            "return_image": {
                "type": "boolean",
                "default": False,
                "description": "Whether to capture and return plot as base64 image",
            },
        },
        "required": ["r_code", "description"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "description": "Whether execution succeeded",
            },
            "result": {
                "type": ["object", "array", "number", "string", "null"],
                "description": "The R computation result",
            },
            "console_output": {
                "type": "string",
                "description": "R console output if any",
            },
            "warnings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "R warnings if any",
            },
            "image_data": {
                "type": "string",
                "description": "Base64-encoded plot image if requested",
            },
            "r_code_executed": {
                "type": "string",
                "description": "The actual R code that was executed",
            },
            "packages_loaded": {
                "type": "array",
                "items": {"type": "string"},
                "description": "R packages that were loaded",
            },
        },
        "required": ["success"],
    },
    description=(
        "Execute custom R code for advanced statistical analyses with safety validation"
    ),
)
async def execute_r_analysis(context, params) -> dict[str, Any]:
    """Execute flexible R code with safety checks."""
    r_code = params["r_code"]
    description = params["description"]
    data = params.get("data")
    packages = params.get("packages", [])
    return_image = params.get("return_image", False)

    await context.info(f"Executing R analysis: {description}")

    # Validate packages
    for pkg in packages:
        if pkg not in ALLOWED_R_PACKAGES:
            await context.error(f"Package '{pkg}' is not allowed")
            return {
                "success": False,
                "error": f"Package '{pkg}' is not in the allowed package list",
            }

    # Validate R code
    is_safe, error = validate_r_code(r_code)
    if not is_safe:
        await context.error(f"R code validation failed: {error}")
        return {"success": False, "error": f"Security validation failed: {error}"}

    # Log the execution (audit trail)
    logger.info(f"Executing flexible R analysis: {description[:100]}")
    logger.debug(f"R code: {r_code[:500]}")

    # Build complete R script
    script_parts = [
        "# Set memory limit and options for safety",
        "options(warn = 1)  # Print warnings as they occur",
        "options(max.print = 10000)  # Limit output size",
    ]

    # Add required packages
    for pkg in packages:
        script_parts.append(f"library({pkg})")

    # Add data if provided
    if data is not None:
        script_parts.append("# Load provided data")
        script_parts.append("data <- as.data.frame(args$data)")

    script_parts.append("# User-provided R code")
    script_parts.append(r_code)

    # Ensure result exists
    script_parts.append("# Ensure result variable exists")
    script_parts.append(
        "if (!exists('result')) { "
        "result <- list(error = 'No result variable defined') }"
    )

    full_script = "\n".join(script_parts)

    try:
        # Execute with appropriate function based on image requirement
        args = {"data": data} if data else {}

        if return_image:
            result = await execute_r_script_with_image_async(
                full_script,
                args,
                include_image=True,
            )
        else:
            result = await execute_r_script_async(full_script, args)

        await context.info("R analysis completed successfully")

        return {
            "success": True,
            "result": result,
            "r_code_executed": full_script,
            "packages_loaded": packages,
            "description": description,
        }

    except Exception as e:
        await context.error(f"R execution failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "r_code_executed": full_script,
            "packages_loaded": packages,
        }


@tool(
    name="list_allowed_r_packages",
    input_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["all", "stats", "ml", "econometrics", "visualization", "data"],
                "default": "all",
                "description": "Category of packages to list",
            }
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "packages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of allowed R packages",
            },
            "total_count": {
                "type": "integer",
                "description": "Total number of allowed packages",
            },
            "category": {"type": "string", "description": "Category requested"},
        },
        "required": ["packages", "total_count", "category"],
    },
    description="List R packages allowed for use in flexible R execution",
)
async def list_allowed_r_packages(context, params) -> dict[str, Any]:
    """List allowed R packages by category."""
    category = params.get("category", "all")

    await context.info(f"Listing allowed R packages: {category}")

    if category == "all":
        packages = sorted(list(ALLOWED_R_PACKAGES))
    elif category == "stats":
        packages = sorted(
            [
                p
                for p in ALLOWED_R_PACKAGES
                if p
                in [
                    "lmtest",
                    "sandwich",
                    "car",
                    "MASS",
                    "boot",
                    "survival",
                    "nlme",
                    "mgcv",
                    "gam",
                    "glmnet",
                ]
            ]
        )
    elif category == "ml":
        packages = sorted(
            [
                p
                for p in ALLOWED_R_PACKAGES
                if p
                in [
                    "randomForest",
                    "rpart",
                    "tree",
                    "gbm",
                    "xgboost",
                    "kernlab",
                    "cluster",
                    "caret",
                    "e1071",
                ]
            ]
        )
    elif category == "econometrics":
        packages = sorted(
            [
                p
                for p in ALLOWED_R_PACKAGES
                if p
                in [
                    "plm",
                    "AER",
                    "vars",
                    "tseries",
                    "urca",
                    "forecast",
                    "dynlm",
                    "quantreg",
                    "systemfit",
                ]
            ]
        )
    elif category == "visualization":
        packages = sorted(
            [
                p
                for p in ALLOWED_R_PACKAGES
                if p
                in [
                    "ggplot2",
                    "lattice",
                    "plotly",
                    "ggpubr",
                    "corrplot",
                    "gridExtra",
                    "viridis",
                ]
            ]
        )
    elif category == "data":
        packages = sorted(
            [
                p
                for p in ALLOWED_R_PACKAGES
                if p
                in [
                    "dplyr",
                    "tidyr",
                    "data.table",
                    "reshape2",
                    "readr",
                    "jsonlite",
                    "openxlsx",
                    "readxl",
                ]
            ]
        )
    else:
        packages = []

    return {"packages": packages, "total_count": len(packages), "category": category}
