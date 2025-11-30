"""
Simple R Script Loader for RMCP Statistical Analysis Tools.

This module provides clean functionality to load R scripts with automatic
infrastructure injection using a template-based approach.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache for loaded scripts to improve performance
_script_cache: dict[str, str] = {}


def get_r_assets_path() -> Path:
    """Get the path to the R assets directory."""
    return Path(__file__).parent


def get_r_script(category: str, script_name: str, include_common: bool = True) -> str:
    """
    Load an R script using template-based approach.

    This function loads R scripts and automatically injects all necessary infrastructure
    using a clean template file approach instead of complex string building.

    Args:
        category: Script category (e.g., "regression", "statistical_tests")
        script_name: Name of the script file (without .R extension)
        include_common: Whether to include common utility scripts (default: True)

    Returns:
        str: Complete R script content ready for execution

    Raises:
        FileNotFoundError: If the requested script file doesn't exist
        ValueError: If category or script_name contains invalid characters
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

    r_assets_path = get_r_assets_path()

    # Load template
    template_path = r_assets_path / "template.R"
    if not template_path.exists():
        raise FileNotFoundError(f"R template not found: {template_path}")

    with open(template_path, encoding="utf-8") as f:
        template = f.read()

    # Load main script
    script_path = r_assets_path / "scripts" / category / f"{script_name}.R"
    if not script_path.exists():
        available_scripts = list_available_scripts(category)
        raise FileNotFoundError(
            f"R script not found: {script_path}\n"
            f"Available scripts in '{category}': {available_scripts}"
        )

    with open(script_path, encoding="utf-8") as f:
        main_script = f.read()

    # Load utilities if requested
    utilities = ""
    if include_common:
        utilities = get_common_utilities()

    # Substitute into template
    complete_script = template.replace("{{ UTILITIES }}", utilities).replace(
        "{{ MAIN_SCRIPT }}", main_script
    )

    # Cache the result
    _script_cache[cache_key] = complete_script

    logger.debug(
        f"Loaded R script: {category}/{script_name} ({len(complete_script)} chars)"
    )
    return complete_script


def get_common_utilities() -> str:
    """Load common R utility functions shared across all scripts."""
    r_assets_path = get_r_assets_path()
    utils_path = r_assets_path / "R" / "utils.R"
    formatting_path = r_assets_path / "common" / "formatting.R"

    script_parts = []

    # Load main utilities
    if utils_path.exists():
        try:
            with open(utils_path, encoding="utf-8") as f:
                script_parts.append(f.read())
        except Exception as e:
            logger.warning(f"Failed to read R utilities: {e}")

    # Load formatting utilities
    if formatting_path.exists():
        try:
            with open(formatting_path, encoding="utf-8") as f:
                if script_parts:  # Add separator if we have utils
                    script_parts.append("")
                script_parts.append("# === FORMATTING UTILITIES ===")
                script_parts.append(f.read())
        except Exception as e:
            logger.warning(f"Failed to read formatting utilities: {e}")

    return "\n".join(script_parts)


def list_available_scripts(category: str | None = None) -> dict[str, list]:
    """List all available R scripts by category."""
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


def clear_script_cache():
    """Clear the R script cache to force reloading from disk."""
    _script_cache.clear()
    logger.info("R script cache cleared")


def get_cache_stats() -> dict[str, int]:
    """Get statistics about the R script cache."""
    return {
        "cached_scripts": len(_script_cache),
        "total_cache_size": sum(len(script) for script in _script_cache.values()),
    }
