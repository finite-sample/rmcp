"""Simple test fixtures for RMCP when needed."""

import json
from pathlib import Path


def load_r_fixture(fixture_name: str) -> dict:
    """
    Load an R fixture from JSON file.

    Args:
        fixture_name: Name of the fixture file (without .json extension)

    Returns:
        The fixture data as a dictionary

    Raises:
        FileNotFoundError: If the fixture file doesn't exist

    Note: Most tests should use actual R execution instead of fixtures.
    This function is only for special cases where pre-captured outputs are needed.
    """
    fixture_path = Path(__file__).parent / f"{fixture_name}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")

    with open(fixture_path, "r") as f:
        return json.load(f)
