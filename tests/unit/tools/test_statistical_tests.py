#!/usr/bin/env python3
"""
Schema validation unit tests for statistical test tools.
Tests input schema validation and output shape compliance without R execution.
"""
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from jsonschema import ValidationError, validate

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from rmcp.tools.statistical_tests import anova, chi_square_test, normality_test, t_test


class TestTTestSchemaValidation:
    """Test t_test input schema validation."""

    def test_valid_one_sample_input(self):
        """Test valid one-sample t-test input."""
        valid_input = {
            "data": {"values": [1, 2, 3, 4, 5]},
            "variable": "values",
            "mu": 0,
            "alternative": "two.sided",
        }
        # Extract schema from tool decorator metadata
        schema = t_test._mcp_tool_input_schema
        # Should not raise ValidationError
        validate(instance=valid_input, schema=schema)

    def test_valid_two_sample_input(self):
        """Test valid two-sample t-test input."""
        valid_input = {
            "data": {
                "values": [1, 2, 3, 4, 5, 6, 7, 8],
                "group": ["A", "A", "A", "A", "B", "B", "B", "B"],
            },
            "variable": "values",
            "group": "group",
            "paired": False,
            "var_equal": False,  # Test new default
        }
        schema = t_test._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_missing_required_parameter(self):
        """Test that missing required parameters are caught."""
        invalid_input = {
            "variable": "values",
            # Missing "data" parameter
        }
        schema = t_test._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        assert "'data' is a required property" in str(exc_info.value)

    def test_invalid_alternative_value(self):
        """Test invalid alternative parameter value."""
        invalid_input = {
            "data": {"values": [1, 2, 3]},
            "variable": "values",
            "alternative": "invalid_option",  # Not in enum
        }
        schema = t_test._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        assert "is not one of" in str(exc_info.value)


class TestChiSquareSchemaValidation:
    """Test chi_square_test input schema validation."""

    def test_valid_independence_test(self):
        """Test valid independence test input."""
        valid_input = {
            "data": {"var1": ["A", "B", "A", "B"], "var2": ["X", "Y", "X", "Y"]},
            "test_type": "independence",
            "x": "var1",
            "y": "var2",
        }
        schema = chi_square_test._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_valid_goodness_of_fit(self):
        """Test valid goodness of fit test input."""
        valid_input = {
            "data": {"category": ["A", "B", "C", "A", "B"]},
            "test_type": "goodness_of_fit",
            "x": "category",
            "expected": [0.3, 0.4, 0.3],  # Valid probabilities
        }
        schema = chi_square_test._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_goodness_of_fit_negative_expected(self):
        """Test that negative expected values are rejected."""
        invalid_input = {
            "data": {"category": ["A", "B", "C"]},
            "test_type": "goodness_of_fit",
            "x": "category",
            "expected": [0.5, -0.2, 0.7],  # Negative value
        }
        schema = chi_square_test._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        assert "is less than the minimum" in str(exc_info.value)

    def test_independence_missing_y_variable(self):
        """Test that independence test y variable validation happens at runtime."""
        # With the flattened schema for Claude compatibility,
        # the validation for y being required for independence test
        # happens at runtime, not at schema validation time
        input_with_missing_y = {
            "data": {"var1": ["A", "B"]},
            "test_type": "independence",
            "x": "var1",
            # Missing "y" parameter - will be caught at runtime
        }
        schema = chi_square_test._mcp_tool_input_schema
        # This now passes schema validation (y is optional in flattened schema)
        # The actual validation happens when the tool is executed
        validate(instance=input_with_missing_y, schema=schema)


class TestAnovaSchemaValidation:
    """Test ANOVA schema validation."""

    def test_valid_anova_input(self):
        """Test valid ANOVA input."""
        valid_input = {
            "data": {
                "response": [1, 2, 3, 4, 5, 6],
                "group": ["A", "A", "B", "B", "C", "C"],
            },
            "formula": "response ~ group",
        }
        schema = anova._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)


class TestNormalityTestSchemaValidation:
    """Test normality test schema validation."""

    def test_valid_normality_test(self):
        """Test valid normality test input."""
        valid_input = {
            "data": {"values": [1, 2, 3, 4, 5]},
            "variable": "values",
            "test": "shapiro",
        }
        schema = normality_test._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_normality_test_schema_structure(self):
        """Test normality test schema structure."""
        schema = normality_test._mcp_tool_input_schema
        # Verify test type enum
        test_enum = schema["properties"]["test"]["enum"]
        assert "shapiro" in test_enum
        assert "jarque_bera" in test_enum
        assert "anderson" in test_enum
        # Verify required fields
        assert "data" in schema["required"]
        assert "variable" in schema["required"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])