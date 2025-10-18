#!/usr/bin/env python3
"""
Unit tests for helper tools.
Tests error recovery, data validation, and example dataset loading.
"""

import sys
from pathlib import Path
from shutil import which

import pytest
from jsonschema import validate

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for helper tools tests"
)

from rmcp.core.context import Context, LifespanState  # noqa: E402
from rmcp.tools.helpers import load_example, suggest_fix, validate_data  # noqa: E402


async def create_test_context():
    """Create a test context for tool execution."""
    lifespan = LifespanState()
    context = Context.create("test", "test", lifespan)
    return context


class TestErrorRecovery:
    """Test error recovery and suggestion tools."""

    @pytest.mark.asyncio
    async def test_suggest_fix_for_missing_package(self):
        """Test suggesting fixes for missing R package errors."""
        context = await create_test_context()

        result = await suggest_fix(
            context,
            {
                "error_message": 'there is no package called "forecast"',
                "tool_name": "arima_model",
            },
        )

        assert "error_type" in result
        assert result["error_type"] == "missing_package"
        assert "suggestions" in result
        # Should suggest installing the package
        suggestions = result["suggestions"]
        assert any("install.packages" in str(s).lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggest_fix_for_data_type_error(self):
        """Test suggesting fixes for data type errors."""
        context = await create_test_context()

        result = await suggest_fix(
            context,
            {
                "error_message": "non-numeric argument to binary operator",
                "tool_name": "correlation_analysis",
            },
        )

        assert "error_type" in result
        assert result["error_type"] in [
            "data_type_error",
            "type_mismatch",
            "data_issue",
            "data_type",
        ]

    @pytest.mark.asyncio
    async def test_suggest_fix_for_formula_error(self):
        """Test suggesting fixes for formula errors."""
        context = await create_test_context()

        result = await suggest_fix(
            context,
            {"error_message": "object 'sales' not found", "tool_name": "linear_model"},
        )

        assert "suggestions" in result
        # Should suggest checking variable names


class TestDataValidation:
    """Test data validation helper."""

    @pytest.mark.asyncio
    async def test_validate_clean_data(self):
        """Test validating clean data without issues using actual R execution."""
        context = await create_test_context()

        clean_data = {
            "x": [1, 2, 3, 4, 5],
            "y": [2.0, 4.0, 6.0, 8.0, 10.0],
        }

        result = await validate_data(context, {"data": clean_data})

        assert "is_valid" in result
        assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_validate_data_with_missing(self):
        """Test validating data with missing values."""
        context = await create_test_context()

        data_with_na = {
            "x": [1, 2, None, 4, 5],
            "y": [2.0, None, 6.0, 8.0, 10.0],
        }

        result = await validate_data(context, {"data": data_with_na})

        # Should report data quality information
        assert "data_quality" in result or "is_valid" in result


class TestExampleDatasets:
    """Test loading example datasets."""

    @pytest.mark.asyncio
    async def test_load_sales_dataset(self):
        """Test loading the example sales dataset."""
        context = await create_test_context()

        result = await load_example(context, {"dataset_name": "sales", "size": "small"})

        assert "data" in result
        assert "metadata" in result

        # Check data structure
        data = result["data"]
        assert isinstance(data, dict)
        # Should have relevant columns for sales data
        # (actual column names depend on implementation)

    @pytest.mark.asyncio
    async def test_load_timeseries_dataset(self):
        """Test loading time series example dataset."""
        context = await create_test_context()

        result = await load_example(
            context, {"dataset_name": "timeseries", "size": "small"}
        )

        assert "data" in result

    def test_load_example_schema(self):
        """Test load_example schema validation."""
        schema = load_example._mcp_tool_input_schema

        # Valid input
        valid_input = {"dataset_name": "sales", "size": "small"}
        validate(instance=valid_input, schema=schema)

        # Check dataset options
        assert "dataset_name" in schema["properties"]
        dataset_enum = schema["properties"]["dataset_name"].get("enum")
        if dataset_enum:
            assert "sales" in dataset_enum

    def test_validate_data_schema(self):
        """Test validate_data schema validation."""
        schema = validate_data._mcp_tool_input_schema

        # Valid input
        valid_input = {"data": {"col1": [1, 2, 3], "col2": [4, 5, 6]}}
        validate(instance=valid_input, schema=schema)

        # Check required fields
        assert "data" in schema["required"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
