"""
R Script Loader for RMCP Statistical Analysis Tools.

This module provides functionality to dynamically load R scripts from the r_assets
directory structure, enabling clean separation between Python tool logic and R
statistical computation code.

Key Features:
- Dynamic R script loading by category and name
- Common utility script inclusion
- Path validation and error handling
- Caching for improved performance
- Support for script composition and includes

Example Usage:
    >>> from rmcp.r_assets.loader import get_r_script
    >>> script = get_r_script("regression", "linear_model")
    >>> print(script[:100])  # Show first 100 characters
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Cache for loaded scripts to improve performance
_script_cache: Dict[str, str] = {}


def get_r_assets_path() -> Path:
    """
    Get the path to the R assets directory.

    Returns:
        Path: Absolute path to the r_assets directory
    """
    return Path(__file__).parent


def get_r_script(category: str, script_name: str, include_common: bool = True) -> str:
    """
    Load an R script from the r_assets directory structure.

    This function loads R scripts organized by category (e.g., "regression",
    "statistical_tests") and optionally includes common utility scripts.

    Args:
        category: Script category (e.g., "regression", "statistical_tests")
        script_name: Name of the script file (without .R extension)
        include_common: Whether to include common utility scripts

    Returns:
        str: Complete R script content ready for execution

    Raises:
        FileNotFoundError: If the requested script file doesn't exist
        ValueError: If category or script_name contains invalid characters

    Example:
        >>> # Load linear regression script
        >>> script = get_r_script("regression", "linear_model")
        >>>
        >>> # Load correlation analysis without common utilities
        >>> script = get_r_script("regression", "correlation", include_common=False)
    """
    # Input validation
    if not category or not script_name:
        raise ValueError("Category and script_name cannot be empty")

    # Validate characters to prevent path traversal
    if any(char in category for char in [".", "/", "\\"]):
        raise ValueError(f"Invalid category name: {category}")
    if any(char in script_name for char in [".", "/", "\\"]):
        raise ValueError(f"Invalid script name: {script_name}")

    # Create cache key
    cache_key = f"{category}:{script_name}:common={include_common}"

    # Check cache first
    if cache_key in _script_cache:
        logger.debug(f"Using cached R script: {cache_key}")
        return _script_cache[cache_key]

    # Build script path
    r_assets_path = get_r_assets_path()
    script_path = r_assets_path / "scripts" / category / f"{script_name}.R"

    # Check if script exists
    if not script_path.exists():
        available_scripts = list_available_scripts(category)
        raise FileNotFoundError(
            f"R script not found: {script_path}\n"
            f"Available scripts in '{category}': {available_scripts}"
        )

    # Load the main script
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            main_script = f.read()
    except Exception as e:
        raise RuntimeError(f"Failed to read R script {script_path}: {e}")

    # Build complete script
    script_parts = []

    # Add common utilities if requested
    if include_common:
        common_script = get_common_utilities()
        if common_script:
            script_parts.append("# === COMMON UTILITIES ===")
            script_parts.append(common_script)
            script_parts.append("")

    # Add main script
    script_parts.append(f"# === {category.upper()} / {script_name.upper()} ===")
    script_parts.append(main_script)

    # Combine all parts
    complete_script = "\n".join(script_parts)

    # Cache the result
    _script_cache[cache_key] = complete_script

    logger.debug(
        f"Loaded R script: {category}/{script_name} ({len(complete_script)} chars)"
    )
    return complete_script


def get_common_utilities() -> str:
    """
    Load common R utility functions shared across all scripts.

    Returns:
        str: Common R utility script content, or empty string if not found
    """
    r_assets_path = get_r_assets_path()
    common_path = r_assets_path / "common" / "formatting.R"

    if not common_path.exists():
        logger.warning(f"Common utilities not found at {common_path}")
        return ""

    try:
        with open(common_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Failed to read common utilities: {e}")
        return ""


def list_available_scripts(category: Optional[str] = None) -> Dict[str, list]:
    """
    List all available R scripts by category.

    Args:
        category: Optional category to filter by. If None, returns all categories.

    Returns:
        Dict[str, list]: Dictionary mapping category names to lists of script names

    Example:
        >>> scripts = list_available_scripts()
        >>> print(scripts["regression"])
        ['linear_model', 'correlation_analysis', 'logistic_regression']

        >>> regression_scripts = list_available_scripts("regression")
        >>> print(regression_scripts)
        {'regression': ['linear_model', 'correlation_analysis']}
    """
    r_assets_path = get_r_assets_path()
    scripts_path = r_assets_path / "scripts"

    if not scripts_path.exists():
        return {}

    available_scripts = {}

    # Get categories to scan
    if category:
        categories = [category] if (scripts_path / category).exists() else []
    else:
        categories = [d.name for d in scripts_path.iterdir() if d.is_dir()]

    for cat in categories:
        cat_path = scripts_path / cat
        script_files = [
            f.stem
            for f in cat_path.glob("*.R")
            if f.is_file() and not f.name.startswith(".")
        ]
        available_scripts[cat] = sorted(script_files)

    return available_scripts


def validate_r_script(script_content: str) -> bool:
    """
    Perform basic validation on R script content.

    Args:
        script_content: R script content to validate

    Returns:
        bool: True if script appears valid, False otherwise

    Note:
        This performs basic syntax checking only. Full validation requires R execution.
    """
    if not script_content or not script_content.strip():
        return False

    # Check for balanced braces and parentheses
    brace_count = script_content.count("{") - script_content.count("}")
    paren_count = script_content.count("(") - script_content.count(")")

    if brace_count != 0 or paren_count != 0:
        logger.warning("R script has unbalanced braces or parentheses")
        return False

    # Check for basic R structure
    essential_patterns = [
        "library(",  # Should load libraries
        "result",  # Should define result variable
    ]

    for pattern in essential_patterns:
        if pattern not in script_content:
            logger.warning(f"R script missing expected pattern: {pattern}")

    return True


def clear_script_cache():
    """Clear the R script cache to force reloading from disk."""
    _script_cache.clear()
    logger.info("R script cache cleared")


def get_cache_stats() -> Dict[str, int]:
    """
    Get statistics about the R script cache.

    Returns:
        Dict with cache statistics
    """
    return {
        "cached_scripts": len(_script_cache),
        "total_cache_size": sum(len(script) for script in _script_cache.values()),
    }
