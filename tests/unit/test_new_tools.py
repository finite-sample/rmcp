"""
Unit tests for the new tools added in v0.3.6:
- Formula builder (natural language to R formulas)
- Error recovery and help tools
- Enhanced file operations (Excel, JSON)
"""

import asyncio
import json
import os

# Add rmcp to path
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.core.context import Context, LifespanState
from rmcp.tools.fileops import read_excel, read_json
from rmcp.tools.formula_builder import build_formula, validate_formula
from rmcp.tools.helpers import load_example, suggest_fix, validate_data


async def create_test_context():
    """Create a test context for tool execution."""
    lifespan = LifespanState()
    context = Context.create("test", "test", lifespan)
    return context


class TestFormulaBuilder:
    """Test natural language formula building."""

    @pytest.mark.asyncio
    async def test_basic_formula_building(self):
        """Test basic formula building from natural language."""
        context = await create_test_context()

        params = {
            "description": "predict sales from marketing spend",
            "analysis_type": "regression",
        }

        result = await build_formula(context, params)

        assert "formula" in result
        assert "sales" in result["formula"]
        assert "marketing" in result["formula"]
        assert "~" in result["formula"]

    @pytest.mark.asyncio
    async def test_multiple_predictors(self):
        """Test formula with multiple predictors."""
        context = await create_test_context()

        params = {
            "description": "customer satisfaction depends on service quality and response time"
        }

        result = await build_formula(context, params)

        assert "formula" in result
        assert "satisfaction" in result["formula"]
        assert "+" in result["formula"] or "and" in result["formula"]

    @pytest.mark.asyncio
    async def test_formula_validation(self):
        """Test formula validation against sample data."""
        context = await create_test_context()

        # Simple test data
        test_data = {"sales": [100, 200, 300, 400], "marketing": [10, 20, 30, 40]}

        params = {"formula": "sales ~ marketing", "data": test_data}

        result = await validate_formula(context, params)

        assert "is_valid" in result
        assert result["is_valid"] == True


class TestErrorRecovery:
    """Test intelligent error recovery tools."""

    @pytest.mark.asyncio
    async def test_package_error_diagnosis(self):
        """Test R package error diagnosis."""
        context = await create_test_context()

        params = {
            "error_message": "there is no package called 'forecast'",
            "tool_name": "arima_model",
        }

        result = await suggest_fix(context, params)

        assert "error_type" in result
        assert result["error_type"] == "missing_package"
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0
        assert "install.packages" in result["suggestions"][0]

    @pytest.mark.asyncio
    async def test_formula_error_diagnosis(self):
        """Test formula syntax error diagnosis."""
        context = await create_test_context()

        params = {
            "error_message": "invalid formula syntax",
            "tool_name": "linear_model",
        }

        result = await suggest_fix(context, params)

        assert "error_type" in result
        assert result["error_type"] == "formula_syntax"
        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_data_validation(self):
        """Test data quality validation."""
        context = await create_test_context()

        # Problematic data
        test_data = {
            "sales": [100, 200, None, 400],  # Missing value
            "marketing": [10, 20, 30, 40],
            "constant": [1, 1, 1, 1],  # Constant variable
        }

        params = {"data": test_data, "analysis_type": "regression"}

        result = await validate_data(context, params)

        assert "is_valid" in result
        assert "warnings" in result
        assert "data_quality" in result


class TestExampleDatasets:
    """Test example dataset loading."""

    @pytest.mark.asyncio
    async def test_load_sales_dataset(self):
        """Test loading sales example dataset."""
        context = await create_test_context()

        params = {"dataset_name": "sales", "size": "small"}

        result = await load_example(context, params)

        assert "data" in result
        assert "metadata" in result
        assert result["metadata"]["name"] == "sales"
        assert result["metadata"]["rows"] > 0
        assert "suggested_analyses" in result

    @pytest.mark.asyncio
    async def test_load_customer_dataset(self):
        """Test loading customer example dataset."""
        context = await create_test_context()

        params = {"dataset_name": "customers", "size": "small"}

        result = await load_example(context, params)

        assert "data" in result
        assert "churned" in str(result["data"])  # Should contain churn data
        assert result["metadata"]["name"] == "customers"


class TestEnhancedFileOps:
    """Test enhanced file operations."""

    @pytest.mark.asyncio
    async def test_json_file_reading(self):
        """Test JSON file reading with flattening."""
        context = await create_test_context()

        # Create test JSON file
        test_data = {
            "results": [
                {"quarter": "Q1", "revenue": 1000, "profit": 100},
                {"quarter": "Q2", "revenue": 1200, "profit": 150},
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            json_file = f.name

        try:
            params = {"file_path": json_file, "flatten": True}

            result = await read_json(context, params)

            assert "data" in result
            assert "file_info" in result
            assert result["file_info"]["rows"] == 2

        finally:
            os.unlink(json_file)


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(TestFormulaBuilder().test_basic_formula_building())
    asyncio.run(TestErrorRecovery().test_package_error_diagnosis())
    asyncio.run(TestExampleDatasets().test_load_sales_dataset())
    print("✅ All unit tests passed!")
