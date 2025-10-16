#!/usr/bin/env python3
"""
Schema validation unit tests for regression tools.
Tests input schema validation and output shape compliance without R execution.
"""
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import validate

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from rmcp.tools.regression import (
    correlation_analysis,
    linear_model,
    logistic_regression,
)


class TestRegressionSchemaValidation:
    """Test regression tool schema validation."""

    def test_linear_model_valid_input(self):
        """Test valid linear model input with realistic business data."""
        # Realistic sales/marketing data from integration tests (R-validated)
        # R output: R² = 0.985, coeffs = (70.58, 5.17), p < 0.001
        valid_input = {
            "data": {
                "sales": [120, 135, 128, 142, 156, 148, 160, 175],
                "marketing": [10, 12, 11, 14, 16, 15, 18, 20],
            },
            "formula": "sales ~ marketing",
            "na_action": "na.omit",
        }
        schema = linear_model._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_correlation_analysis_valid_input(self):
        """Test valid correlation analysis input with realistic economic data."""
        # Realistic macroeconomic data from integration tests (R-validated)
        # R output: GDP-unemployment correlation = -0.97 (Okun's Law)
        valid_input = {
            "data": {
                "gdp_growth": [2.1, 2.3, 1.8, 2.5, 2.7, 2.2],
                "unemployment": [5.2, 5.0, 5.5, 4.8, 4.5, 4.9],
                "inflation": [1.5, 1.8, 2.1, 1.9, 2.3, 2.0],
            },
            "variables": ["gdp_growth", "unemployment", "inflation"],
            "method": "pearson",
            "confidence_level": 0.95,
        }
        schema = correlation_analysis._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_logistic_regression_valid_input(self):
        """Test valid logistic regression input with realistic customer data."""
        # Realistic customer churn data from integration tests (R-validated)
        # R output: Model converges, tenure reduces churn probability
        valid_input = {
            "data": {
                "churn": [0, 1, 0, 1, 0, 0, 1, 1, 0, 1],
                "tenure_months": [24, 6, 36, 3, 48, 18, 9, 2, 60, 4],
                "monthly_charges": [70, 85, 65, 90, 60, 75, 95, 100, 55, 88],
            },
            "formula": "churn ~ tenure_months + monthly_charges",
            "family": "binomial",
        }
        schema = logistic_regression._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_linear_model_output_structure(self):
        """Test linear_model returns expected output structure."""
        # Verify the function signature and imports work
        assert callable(linear_model)
        assert hasattr(linear_model, "_mcp_tool_input_schema")
        assert linear_model.__annotations__["return"] == dict[str, Any]

    def test_correlation_analysis_methods(self):
        """Test correlation analysis method options."""
        schema = correlation_analysis._mcp_tool_input_schema
        method_enum = schema["properties"]["method"]["enum"]
        assert "pearson" in method_enum
        assert "spearman" in method_enum
        assert "kendall" in method_enum


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
