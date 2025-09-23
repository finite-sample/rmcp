"""
Test R Script Loader for RMCP Tests.
Provides utilities for loading R scripts from the tests/r_scripts directory
for use in test cases.
"""

import os
from pathlib import Path
from typing import Dict


def get_test_r_script(category: str, script_name: str) -> str:
    """
    Load a test R script from the tests/r_scripts directory.

    Args:
        category: Subdirectory under tests/r_scripts
                 (e.g., 'flexible_r', 'integration', 'e2e')
        script_name: Name of the R script file without .R extension

    Returns:
        str: Content of the R script

    Raises:
        FileNotFoundError: If the script file doesn't exist
    """
    # Get the tests directory (parent of this file)
    tests_dir = Path(__file__).parent
    script_path = tests_dir / "r_scripts" / category / f"{script_name}.R"

    if not script_path.exists():
        raise FileNotFoundError(f"Test R script not found: {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        return f.read()


def list_test_r_scripts(category: str = None) -> Dict[str, list]:
    """
    List available test R scripts.

    Args:
        category: If provided, list scripts in that category only

    Returns:
        Dict mapping category names to lists of script names
        (without .R extension)
    """
    tests_dir = Path(__file__).parent
    r_scripts_dir = tests_dir / "r_scripts"

    if not r_scripts_dir.exists():
        return {}

    result = {}

    if category:
        # List scripts in specific category
        category_dir = r_scripts_dir / category
        if category_dir.exists():
            scripts = [f.stem for f in category_dir.glob("*.R")]
            result[category] = sorted(scripts)
    else:
        # List all categories and their scripts
        for category_dir in r_scripts_dir.iterdir():
            if category_dir.is_dir():
                scripts = [f.stem for f in category_dir.glob("*.R")]
                result[category_dir.name] = sorted(scripts)

    return result


# Convenience functions for common test script categories
def get_flexible_r_script(script_name: str) -> str:
    """Load a flexible R test script."""
    return get_test_r_script("flexible_r", script_name)


def get_integration_r_script(script_name: str) -> str:
    """Load an integration test R script."""
    return get_test_r_script("integration", script_name)


def get_e2e_r_script(script_name: str) -> str:
    """Load an end-to-end test R script."""
    return get_test_r_script("e2e", script_name)
