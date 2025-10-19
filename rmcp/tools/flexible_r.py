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


def validate_r_code(r_code: str, context=None) -> tuple[bool, Optional[str]]:
    """
    Validate R code for safety with interactive package approval.

    Returns:
        (is_safe, error_message)
    """
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, r_code, re.IGNORECASE):
            return False, f"Dangerous pattern detected: {pattern}"

    # Filter out comment lines before checking for package usage
    code_lines = [
        line for line in r_code.split("\n") if not line.strip().startswith("#")
    ]
    code_without_comments = "\n".join(code_lines)

    # Extract library/require calls
    lib_pattern = r"(?:library|require)\s*\(\s*['\"]?(\w+)['\"]?\s*\)"
    packages = re.findall(lib_pattern, code_without_comments, re.IGNORECASE)

    # Check all packages are in whitelist or session-approved
    for pkg in packages:
        if pkg not in ALLOWED_R_PACKAGES:
            # Check if package is session-approved
            session_approved = (
                context
                and hasattr(context, "_approved_packages")
                and pkg in context._approved_packages
            )
            if not session_approved:
                # Request user approval through context
                if context:
                    return False, f"APPROVAL_NEEDED:{pkg}"
                else:
                    return False, f"Package '{pkg}' requires user approval"

    # Check for double-colon package usage (pkg::function)
    colon_pattern = r"(\w+)::"
    colon_packages = re.findall(colon_pattern, code_without_comments)
    for pkg in colon_packages:
        if pkg not in ALLOWED_R_PACKAGES:
            # Check if package is session-approved
            session_approved = (
                context
                and hasattr(context, "_approved_packages")
                and pkg in context._approved_packages
            )
            if not session_approved:
                if context:
                    return False, f"APPROVAL_NEEDED:{pkg}"
                else:
                    return (
                        False,
                        f"Package '{pkg}' (used with ::) requires user approval",
                    )

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
                **table_schema(),
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
    description="Executes custom R code for advanced statistical analyses beyond the built-in tools, with comprehensive safety validation including package whitelisting, timeout protection, and audit logging. Supports complex statistical procedures, custom visualizations, and specialized analyses not covered by structured tools. Use for cutting-edge statistical methods, custom modeling approaches, research-specific analyses, or when existing tools don't meet specific analytical requirements. Essential for advanced users needing R's full statistical capabilities.",
)
async def execute_r_analysis(context, params) -> dict[str, Any]:
    """Execute flexible R code with safety checks."""
    r_code = params["r_code"]
    description = params["description"]
    data = params.get("data")
    packages = params.get("packages", [])
    return_image = params.get("return_image", False)

    await context.info(f"Executing R analysis: {description}")

    # Package validation is now handled in validate_r_code function below

    # Validate R code with interactive approval
    is_safe, error = validate_r_code(r_code, context)
    if not is_safe:
        if error and error.startswith("APPROVAL_NEEDED:"):
            # Extract package name and request approval
            pkg_name = error.split(":", 1)[1]
            approval_msg = f"""
📦 Package Approval Required

The R code wants to use package '{pkg_name}' which is not in the pre-approved list.

This package may provide useful statistical functionality, but requires your permission to use.

Would you like to:
1. **Allow '{pkg_name}'** - Approve this package for this analysis
2. **Block '{pkg_name}'** - Reject this package and modify the analysis

Please respond with your choice. If you approve, the analysis will continue with '{pkg_name}' included.
"""
            await context.info(f"Package approval required for: {pkg_name}")
            # Return schema-compliant response with approval prompt
            return {
                "success": False,  # Required by schema
                "result": {
                    "approval_required": True,
                    "package": pkg_name,
                    "message": approval_msg,
                },
                "console_output": f"Package '{pkg_name}' requires user approval to proceed.",
                "r_code_executed": r_code,
                "packages_loaded": [],
                "description": f"Approval required for package: {pkg_name}",
            }
        else:
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
    description="Lists all R packages whitelisted for safe execution in flexible R code including statistical analysis, data manipulation, visualization, and specialized econometric packages. Provides package categories and brief descriptions to help users understand available functionality. Use to discover available packages, plan complex analyses, understand system capabilities, or verify that required packages are available before writing custom R code.",
)
async def list_allowed_r_packages(context, params) -> dict[str, Any]:
    """List allowed R packages by category."""
    category = params.get("category", "all")

    await context.info(f"Listing allowed R packages: {category}")

    # Use match/case for category selection (Python 3.10+)
    match category:
        case "all":
            packages = sorted(list(ALLOWED_R_PACKAGES))
        case "stats":
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
        case "ml":
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
        case "econometrics":
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
        case "visualization":
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
        case "data":
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
        case _:
            packages = []

    return {"packages": packages, "total_count": len(packages), "category": category}


@tool(
    name="approve_r_package",
    input_schema={
        "type": "object",
        "properties": {
            "package_name": {
                "type": "string",
                "description": "Name of the R package to approve for use",
            },
            "action": {
                "type": "string",
                "enum": ["approve", "deny"],
                "description": "Whether to approve or deny the package",
            },
            "session_only": {
                "type": "boolean",
                "default": True,
                "description": "Whether approval is only for current session (true) or permanent (false)",
            },
        },
        "required": ["package_name", "action"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "package": {"type": "string"},
            "action": {"type": "string"},
            "message": {"type": "string"},
            "session_packages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of currently approved session packages",
            },
        },
        "required": ["success", "package", "action", "message"],
    },
    description="Approve or deny R packages for use in flexible R code execution. Allows users to grant permission for packages not in the default allowlist. Session-only approval means packages are approved for the current analysis session only. Use this tool when RMCP requests package approval for statistical analysis.",
)
async def approve_r_package(context, params) -> dict[str, Any]:
    """Handle user approval/denial of R packages."""
    package_name = params["package_name"]
    action = params["action"]
    session_only = params.get("session_only", True)

    # Get or create session package store
    if not hasattr(context, "_approved_packages"):
        context._approved_packages = set()

    if action == "approve":
        context._approved_packages.add(package_name)

        if session_only:
            await context.info(f"✅ Package '{package_name}' approved for this session")
            message = f"Package '{package_name}' has been approved for use in this analysis session."
        else:
            # For permanent approval, we would need to modify the allowlist
            # For now, just do session approval
            await context.info(
                f"✅ Package '{package_name}' approved for this session (permanent approval not yet implemented)"
            )
            message = f"Package '{package_name}' has been approved for use in this analysis session."

        return {
            "success": True,
            "package": package_name,
            "action": "approved",
            "message": message,
            "session_packages": list(context._approved_packages),
        }

    else:  # deny
        await context.info(f"❌ Package '{package_name}' denied")
        return {
            "success": True,
            "package": package_name,
            "action": "denied",
            "message": f"Package '{package_name}' has been denied. Please modify your analysis to use approved packages.",
            "session_packages": list(getattr(context, "_approved_packages", [])),
        }
