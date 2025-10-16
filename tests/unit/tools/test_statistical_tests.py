#!/usr/bin/env python3
"""
Schema validation unit tests for statistical test tools.
Tests input schema validation and output shape compliance without R execution.
"""
import sys
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from rmcp.tools.statistical_tests import anova, chi_square_test, normality_test, t_test


class TestTTestSchemaValidation:
    """Test t_test input schema validation."""

    def test_valid_one_sample_input(self):
        """Test valid one-sample t-test input with realistic test scores."""
        # Realistic test scores data (R-validated: mean = 83.3)
        valid_input = {
            "data": {"test_scores": [78, 82, 85, 79, 88, 84, 81, 86, 83, 87]},
            "variable": "test_scores",
            "mu": 80,
            "alternative": "two.sided",
        }
        # Extract schema from tool decorator metadata
        schema = t_test._mcp_tool_input_schema
        # Should not raise ValidationError
        validate(instance=valid_input, schema=schema)

    def test_valid_two_sample_input(self):
        """Test valid two-sample t-test input with realistic teaching methods."""
        # Realistic teaching method comparison (R-validated: t=6.27, p<0.001)
        valid_input = {
            "data": {
                "test_scores": [
                    78,
                    82,
                    85,
                    79,
                    88,
                    84,
                    81,
                    86,
                    83,
                    87,
                    73,
                    76,
                    74,
                    78,
                    75,
                    77,
                    74,
                    79,
                    76,
                    75,
                ],
                "method": [
                    "A",
                    "A",
                    "A",
                    "A",
                    "A",
                    "A",
                    "A",
                    "A",
                    "A",
                    "A",
                    "B",
                    "B",
                    "B",
                    "B",
                    "B",
                    "B",
                    "B",
                    "B",
                    "B",
                    "B",
                ],
            },
            "variable": "test_scores",
            "group": "method",
            "paired": False,
            "var_equal": False,  # Test new default
        }
        schema = t_test._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_missing_required_parameter(self):
        """Test that missing required parameters are caught."""
        invalid_input = {
            "variable": "test_scores",
            # Missing "data" parameter
        }
        schema = t_test._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        assert "'data' is a required property" in str(exc_info.value)

    def test_invalid_alternative_value(self):
        """Test invalid alternative parameter value."""
        invalid_input = {
            "data": {"test_scores": [78, 82, 85]},
            "variable": "test_scores",
            "alternative": "invalid_option",  # Not in enum
        }
        schema = t_test._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        assert "is not one of" in str(exc_info.value)


class TestChiSquareSchemaValidation:
    """Test chi_square_test input schema validation."""

    def test_valid_independence_test(self):
        """Test valid independence test input with realistic survey data."""
        # Realistic employee satisfaction survey (R-validated: chi-sq=3.53, p=0.47)
        valid_input = {
            "data": {
                "satisfaction": [
                    "Satisfied",
                    "Neutral",
                    "Satisfied",
                    "Dissatisfied",
                    "Satisfied",
                    "Neutral",
                    "Satisfied",
                    "Satisfied",
                    "Neutral",
                    "Dissatisfied",
                ],
                "department": [
                    "Sales",
                    "Sales",
                    "Marketing",
                    "Marketing",
                    "HR",
                    "HR",
                    "Sales",
                    "Marketing",
                    "HR",
                    "Sales",
                ],
            },
            "test_type": "independence",
            "x": "satisfaction",
            "y": "department",
        }
        schema = chi_square_test._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_valid_goodness_of_fit(self):
        """Test valid goodness of fit test input with realistic market share data."""
        # Realistic market share analysis
        valid_input = {
            "data": {
                "brand_choice": [
                    "BrandA",
                    "BrandB",
                    "BrandC",
                    "BrandA",
                    "BrandB",
                    "BrandA",
                    "BrandC",
                    "BrandB",
                    "BrandA",
                    "BrandC",
                ]
            },
            "test_type": "goodness_of_fit",
            "x": "brand_choice",
            "expected": [0.4, 0.35, 0.25],  # Expected market shares
        }
        schema = chi_square_test._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_goodness_of_fit_negative_expected(self):
        """Test that negative expected values are rejected."""
        invalid_input = {
            "data": {"brand_choice": ["BrandA", "BrandB", "BrandC"]},
            "test_type": "goodness_of_fit",
            "x": "brand_choice",
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
            "data": {"satisfaction": ["Satisfied", "Neutral"]},
            "test_type": "independence",
            "x": "satisfaction",
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
                "test_scores": [85, 88, 78, 82, 90, 87, 75, 79, 92, 89, 73, 77],
                "teaching_method": [
                    "Method1",
                    "Method1",
                    "Method1",
                    "Method1",
                    "Method2",
                    "Method2",
                    "Method2",
                    "Method2",
                    "Method3",
                    "Method3",
                    "Method3",
                    "Method3",
                ],
            },
            "formula": "test_scores ~ teaching_method",
        }
        schema = anova._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)


class TestNormalityTestSchemaValidation:
    """Test normality test schema validation."""

    def test_valid_normality_test(self):
        """Test valid normality test input."""
        valid_input = {
            "data": {"test_scores": [78, 82, 85, 79, 88, 84, 81, 86, 83, 87]},
            "variable": "test_scores",
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
