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
        """Test valid linear model input."""
        valid_input = {
            "data": {"y": [1, 2, 3, 4], "x": [10, 20, 30, 40]},
            "formula": "y ~ x",
            "na_action": "na.omit",
        }
        schema = linear_model._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_correlation_analysis_valid_input(self):
        """Test valid correlation analysis input."""
        valid_input = {
            "data": {
                "var1": [1, 2, 3, 4, 5],
                "var2": [2, 4, 6, 8, 10],
                "var3": [1, 3, 5, 7, 9],
            },
            "variables": ["var1", "var2", "var3"],
            "method": "pearson",
            "confidence_level": 0.95,
        }
        schema = correlation_analysis._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_logistic_regression_valid_input(self):
        """Test valid logistic regression input."""
        valid_input = {
            "data": {
                "outcome": [0, 0, 1, 1, 0, 1],
                "predictor": [1, 2, 3, 4, 5, 6],
            },
            "formula": "outcome ~ predictor",
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
