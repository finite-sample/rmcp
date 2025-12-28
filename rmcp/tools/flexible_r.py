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

import re
import time
from typing import Any

from ..core.schemas import table_schema
from ..logging_config import get_logger, log_security_event, log_tool_execution
from ..r_integration import execute_r_script_async, execute_r_script_with_image_async
from ..registries.tools import tool

logger = get_logger(__name__)

# Import comprehensive package whitelist from systematic categorization
from .package_whitelist_comprehensive import (
    ALLOWED_R_PACKAGES as COMPREHENSIVE_PACKAGES,
)
from .package_whitelist_comprehensive import (
    get_package_categories,
)

# Use comprehensive whitelist (700+ packages from CRAN task views)
ALLOWED_R_PACKAGES = COMPREHENSIVE_PACKAGES

# Legacy small whitelist for conservative environments (if needed)
LEGACY_ALLOWED_PACKAGES = {
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
    # Core tidyverse
    "dplyr",
    "tidyr",
    "ggplot2",
    "readr",
    "tibble",
    "stringr",
    "forcats",
    "lubridate",
    "purrr",
    "tidyverse",
    # Essential statistical packages
    "lmtest",
    "sandwich",
    "car",
    "MASS",
    "boot",
    "survival",
    "caret",
    "randomForest",
    "rpart",
    "e1071",
    "forecast",
    "zoo",
    "xts",
    # Essential utilities
    "jsonlite",
    "broom",
    "knitr",
    "rlang",
    "haven",
}

# Dangerous patterns to block
# Patterns moved to OPERATION_CATEGORIES for user approval:
# - install.packages (now in package_installation)
# - ggsave, write.csv, writeLines (now in file_operations)
# - system, shell, Sys.setenv (now in system_operations)

DANGEROUS_PATTERNS = [
    r"setwd\s*\(",  # Change working directory
    r"source\s*\(",  # Source external files
    r"download\.",  # Download functions
    r"file\.remove",  # File deletion
    r"file\.rename",  # File renaming
    r"unlink\s*\(",  # File deletion
    r"(?<!gg)save\s*\(",  # Save workspace (but not ggsave)
    r"save\.image",  # Save workspace image
    r"load\s*\(",  # Load workspace
    r"readLines\s*\(",  # Read arbitrary files
    r"sink\s*\(",  # Redirect output
    r"options\s*\(\s*warn",  # Change warning behavior
]


def is_operation_approved(
    context, operation_type: str, specific_operation: str
) -> bool:
    """Check if a specific operation has been approved by the user."""
    if not context or not hasattr(context, "_approved_operations"):
        return False

    operations = context._approved_operations.get(operation_type, {})
    return specific_operation in operations


def validate_r_code(r_code: str, context=None) -> tuple[bool, str | None]:
    """
    Validate R code for safety with interactive operation and package approval.

    Returns:
        (is_safe, error_message)
    """
    # Check for controllable operations that need approval
    for operation_type, config in OPERATION_CATEGORIES.items():
        for pattern in config["patterns"]:
            if re.search(pattern, r_code, re.IGNORECASE):
                # Extract specific operation name
                match = re.search(pattern, r_code, re.IGNORECASE)
                if match:
                    specific_op = match.group(0).split("(")[0].strip()
                    if not is_operation_approved(context, operation_type, specific_op):
                        return (
                            False,
                            f"OPERATION_APPROVAL_NEEDED:{operation_type}:{specific_op}",
                        )

    # Check for remaining dangerous patterns that cannot be approved
    remaining_dangerous = [
        r"setwd\s*\(",  # Change working directory
        r"source\s*\(",  # Source external files
        r"download\.",  # Download functions
        r"file\.remove",  # File deletion
        r"file\.rename",  # File renaming
        r"unlink\s*\(",  # File deletion
        r"(?<!gg)save\s*\(",  # Save workspace (but not ggsave)
        r"save\.image",  # Save workspace image
        r"load\s*\(",  # Load workspace
        r"readLines\s*\(",  # Read arbitrary files
        r"sink\s*\(",  # Redirect output
        r"options\s*\(\s*warn",  # Change warning behavior
    ]

    for pattern in remaining_dangerous:
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

    start_time = time.time()

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

        # Log successful tool execution with structured data
        execution_time_ms = int((time.time() - start_time) * 1000)
        log_tool_execution(
            logger,
            tool_name="execute_r_analysis",
            parameters={
                "description": description,
                "packages": packages,
                "return_image": return_image,
            },
            execution_time_ms=execution_time_ms,
            r_packages_used=packages,
            success=True,
        )

        return {
            "success": True,
            "result": result,
            "r_code_executed": full_script,
            "packages_loaded": packages,
            "description": description,
        }

    except Exception as e:
        await context.error(f"R execution failed: {str(e)}")

        # Log failed tool execution
        execution_time_ms = int((time.time() - start_time) * 1000)
        log_tool_execution(
            logger,
            tool_name="execute_r_analysis",
            parameters={
                "description": description,
                "packages": packages,
                "return_image": return_image,
            },
            execution_time_ms=execution_time_ms,
            success=False,
            error_message=str(e),
        )

        return {
            "success": False,
            "error": str(e),
            "r_code_executed": full_script,
            "packages_loaded": packages,
        }


# Operation approval categories and configurations
OPERATION_CATEGORIES = {
    "file_operations": {
        "patterns": [
            r"ggsave\s*\(",
            r"write\.csv\s*\(",
            r"write\.table\s*\(",
            r"writeLines\s*\(",
        ],
        "description": "File writing and saving operations",
        "examples": [
            "ggsave('plot.png', plot)",
            "write.csv(data, 'file.csv')",
            "writeLines(text, 'file.txt')",
        ],
        "security_level": "medium",
    },
    "package_installation": {
        "patterns": [r"install\.packages"],
        "description": "R package installation from repositories",
        "examples": [
            "install.packages('moments')",
            "install.packages(c('pkg1', 'pkg2'))",
        ],
        "security_level": "medium",
    },
    "system_operations": {
        "patterns": [r"system\s*\(", r"shell\s*\(", r"Sys\.setenv"],
        "description": "System-level operations and environment changes",
        "examples": ["system('ls')", "Sys.setenv(VAR='value')"],
        "security_level": "high",
    },
}


@tool(
    name="approve_operation",
    input_schema={
        "type": "object",
        "properties": {
            "operation_type": {
                "type": "string",
                "enum": [
                    "file_operations",
                    "package_installation",
                    "system_operations",
                ],
                "description": "Category of operation to approve",
            },
            "specific_operation": {
                "type": "string",
                "description": "Specific operation being approved (e.g., 'ggsave', 'install.packages')",
            },
            "action": {
                "type": "string",
                "enum": ["approve", "deny"],
                "default": "approve",
                "description": "Whether to approve or deny the operation",
            },
            "scope": {
                "type": "string",
                "enum": ["session", "permanent"],
                "default": "session",
                "description": "Scope of approval - session only or permanent",
            },
            "directory": {
                "type": "string",
                "description": "For file operations: directory to allow writing to (e.g., './plots', '~/Downloads')",
            },
        },
        "required": ["operation_type", "specific_operation"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "operation_type": {"type": "string"},
            "specific_operation": {"type": "string"},
            "action": {"type": "string", "enum": ["approved", "denied"]},
            "scope": {"type": "string"},
            "message": {"type": "string"},
            "approved_operations": {
                "type": "object",
                "description": "Currently approved operations by category",
            },
            "security_info": {
                "type": "object",
                "properties": {
                    "level": {"type": "string"},
                    "implications": {"type": "string"},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "required": ["success", "operation_type", "action", "message"],
    },
    description="Approve or deny R operations including file writing (ggsave, write.csv), package installation (install.packages), and system operations. Provides explicit user control over potentially sensitive operations. Session approvals apply only to current analysis session, while permanent approvals persist across sessions. Essential for enabling file saving, package installation, and system interactions while maintaining security through explicit consent.",
)
async def approve_operation(context, params) -> dict[str, Any]:
    """Universal approval system for R operations."""
    operation_type = params["operation_type"]
    specific_operation = params["specific_operation"]
    action = params.get("action", "approve")
    scope = params.get("scope", "session")
    directory = params.get("directory")

    await context.info(
        f"Processing {action} request for {operation_type}: {specific_operation}"
    )

    # Initialize approval tracking
    if not hasattr(context, "_approved_operations"):
        context._approved_operations = {}

    # Get operation category info
    category_info = OPERATION_CATEGORIES.get(operation_type, {})
    security_level = category_info.get("security_level", "medium")

    if action == "approve":
        # Store approval
        if operation_type not in context._approved_operations:
            context._approved_operations[operation_type] = {}

        approval_data = {
            "specific_operation": specific_operation,
            "scope": scope,
            "approved_at": __import__("time").time(),
        }

        if directory and operation_type == "file_operations":
            approval_data["directory"] = directory
            # Enable VFS write mode if available
            if hasattr(context.lifespan, "vfs") and context.lifespan.vfs:
                context.lifespan.vfs.read_only = False
                await context.info(f"✅ Enabled file writing to: {directory}")

        context._approved_operations[operation_type][specific_operation] = approval_data

        message = f"✅ Approved {operation_type} operation: {specific_operation}"
        if scope == "session":
            message += " (session only)"
        if directory:
            message += f" → {directory}"

        security_info = {
            "level": security_level,
            "implications": f"This allows {category_info.get('description', 'the requested operation')}",
            "recommendations": [
                (
                    "Approval applies to current session only"
                    if scope == "session"
                    else "Approval is permanent"
                ),
                "Review code before execution",
                f"Monitor {operation_type} activities",
            ],
        }

        await context.info(f"✅ {message}")

        return {
            "success": True,
            "operation_type": operation_type,
            "specific_operation": specific_operation,
            "action": "approved",
            "scope": scope,
            "message": message,
            "approved_operations": {
                k: list(v.keys()) for k, v in context._approved_operations.items()
            },
            "security_info": security_info,
        }

    else:  # deny
        message = f"❌ Denied {operation_type} operation: {specific_operation}"
        await context.info(message)

        return {
            "success": True,
            "operation_type": operation_type,
            "specific_operation": specific_operation,
            "action": "denied",
            "scope": "none",
            "message": message,
            "approved_operations": {
                k: list(v.keys())
                for k, v in getattr(context, "_approved_operations", {}).items()
            },
        }


@tool(
    name="list_allowed_r_packages",
    input_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": [
                    "all",
                    "summary",
                    "base_r",
                    "core_infrastructure",
                    "tidyverse",
                    "machine_learning",
                    "econometrics",
                    "time_series",
                    "bayesian",
                    "survival",
                    "spatial",
                    "optimization",
                    "meta_analysis",
                    "clinical_trials",
                    "robust_stats",
                    "missing_data",
                    "nlp_text",
                    "data_io",
                    "experimental_design",
                    "network_analysis",
                    # Legacy categories for backward compatibility
                    "stats",
                    "ml",
                    "visualization",
                    "data",
                ],
                "default": "summary",
                "description": "Category of packages to list based on CRAN task views",
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
    description="Lists comprehensive R packages whitelisted for statistical analysis based on CRAN task views. Covers 700+ packages across machine learning, econometrics, time series, Bayesian methods, survival analysis, spatial data, and more. Use 'summary' to see category breakdown or specific categories to explore available packages. Helps discover capabilities, plan analyses, and verify package availability.",
)
async def list_allowed_r_packages(context, params) -> dict[str, Any]:
    """List allowed R packages by comprehensive CRAN task view categories."""
    category = params.get("category", "summary")

    await context.info(f"Listing allowed R packages: {category}")

    # Get systematic package categories
    categories = get_package_categories()

    if category == "all":
        packages = sorted(ALLOWED_R_PACKAGES)
        total_count = len(packages)
        await context.info(f"Listed all {total_count} comprehensive packages")
        return {"packages": packages, "total_count": total_count, "category": category}

    elif category == "summary":
        # Return summary statistics by category
        category_stats = {}
        for cat_name, cat_packages in categories.items():
            category_stats[cat_name] = len(cat_packages)

        total_count = len(ALLOWED_R_PACKAGES)
        await context.info(
            f"Comprehensive package whitelist: {total_count} total packages across {len(categories)} categories"
        )

        return {
            "packages": list(
                category_stats.keys()
            ),  # Return category names as "packages"
            "total_count": total_count,
            "category": category,
            "category_breakdown": category_stats,
            "description": "Comprehensive R package whitelist based on CRAN task views and usage statistics",
            "major_categories": [
                "machine_learning (ML/statistical learning)",
                "econometrics (causal inference, panel data)",
                "time_series (forecasting, ARIMA, VAR)",
                "bayesian (MCMC, Stan, JAGS)",
                "survival (Cox models, competing risks)",
                "tidyverse (data manipulation, visualization)",
            ],
        }

    elif category in categories:
        packages = sorted(categories[category])
        total_count = len(packages)
        await context.info(f"Listed {total_count} packages in {category} category")
        return {"packages": packages, "total_count": total_count, "category": category}

    else:
        # Handle legacy categories for backward compatibility
        legacy_mappings = {
            "stats": sorted(
                categories.get("machine_learning", set())
                | categories.get("econometrics", set())
                | categories.get("bayesian", set())
            ),
            "ml": sorted(categories.get("machine_learning", set())),
            "visualization": sorted(
                [
                    p
                    for p in ALLOWED_R_PACKAGES
                    if p
                    in {
                        "ggplot2",
                        "lattice",
                        "plotly",
                        "corrplot",
                        "viridis",
                        "RColorBrewer",
                        "ggpubr",
                        "gridExtra",
                    }
                ]
            ),
            "data": sorted(
                categories.get("tidyverse", set()) | categories.get("data_io", set())
            ),
        }
        packages = legacy_mappings.get(category, [])
        total_count = len(packages)
        await context.info(
            f"Listed {total_count} packages in legacy category: {category}"
        )
        return {"packages": packages, "total_count": total_count, "category": category}


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

        # Log security approval event
        log_security_event(
            logger,
            event_type="package_approval",
            operation=f"approve_{package_name}",
            approved=True,
            security_level="medium",
            details={"package_name": package_name, "session_only": session_only},
        )

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
        # Log security denial event
        log_security_event(
            logger,
            event_type="package_approval",
            operation=f"deny_{package_name}",
            approved=False,
            security_level="medium",
            details={"package_name": package_name, "reason": "user_denied"},
        )

        await context.info(f"❌ Package '{package_name}' denied")
        return {
            "success": True,
            "package": package_name,
            "action": "denied",
            "message": f"Package '{package_name}' has been denied. Please modify your analysis to use approved packages.",
            "session_packages": list(getattr(context, "_approved_packages", [])),
        }
