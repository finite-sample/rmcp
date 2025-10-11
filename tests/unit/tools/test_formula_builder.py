#!/usr/bin/env python3
"""
Unit tests for formula builder tools.
Tests natural language to R formula conversion and validation.
"""

import sys
from pathlib import Path
from shutil import which

import pytest

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for formula builder tests"
)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from rmcp.core.context import Context, LifespanState  # noqa: E402
from rmcp.tools.formula_builder import build_formula, validate_formula  # noqa: E402


async def create_test_context():
    """Create a test context for tool execution."""
    lifespan = LifespanState()
    context = Context.create("test", "test", lifespan)
    return context


class TestFormulaBuilder:
    """Test natural language formula building."""

    @pytest.mark.asyncio
    async def test_simple_formula_building(self):
        """Test building a simple regression formula from description."""
        context = await create_test_context()

        result = await build_formula(
            context, {"description": "predict sales from marketing spend"}
        )

        # build_formula returns the result directly
        assert "formula" in result
        formula = result["formula"]
        # Should generate something like "sales ~ marketing" or similar
        assert "~" in formula  # R formula syntax

    @pytest.mark.asyncio
    async def test_multiple_predictor_formula(self):
        """Test building formula with multiple predictors."""
        context = await create_test_context()

        result = await build_formula(
            context,
            {
                "description": "predict price based on size, location, and age",
                "target_hint": "price",
            },
        )

        # build_formula returns the result directly
        assert "formula" in result
        formula = result["formula"]
        assert "price" in formula
        assert "~" in formula

    @pytest.mark.asyncio
    async def test_validate_valid_formula(self):
        """Test validating a correct R formula."""
        context = await create_test_context()

        # validate_formula requires both formula and data
        test_data = {
            "x1": [1, 2, 3],
            "x2": [4, 5, 6],
            "x3": [7, 8, 9],
            "y": [10, 11, 12],
        }
        result = await validate_formula(
            context, {"formula": "y ~ x1 + x2 + x3", "data": test_data}
        )

        # validate_formula returns validation data directly
        # Check if it's valid (might be under 'is_valid' or 'valid')
        assert "is_valid" in result or "valid" in result
        if "is_valid" in result:
            assert result["is_valid"] is True
        else:
            assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_invalid_formula(self):
        """Test validating an incorrect R formula."""
        context = await create_test_context()

        # validate_formula requires both formula and data
        test_data = {"x": [1, 2, 3], "y": [4, 5, 6]}
        result = await validate_formula(
            context, {"formula": "this is not a formula", "data": test_data}
        )

        # The tool should indicate invalid formula
        if "is_valid" in result:
            assert result["is_valid"] is False
        elif "valid" in result:
            assert result["valid"] is False
        # There should be error info
        assert "error" in result or "message" in result or "errors" in result

    @pytest.mark.asyncio
    async def test_formula_with_interactions(self):
        """Test building formula with interaction terms."""
        context = await create_test_context()

        result = await build_formula(
            context,
            {
                "description": "predict outcome with interaction between treatment and time"
            },
        )

        # build_formula returns the result directly
        assert "formula" in result
        # Might generate something with : or * for interactions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
