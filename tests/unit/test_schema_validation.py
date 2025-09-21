#!/usr/bin/env python3
"""
Schema validation unit tests for RMCP.
Tests input schema validation and output shape compliance without R execution.
These tests ensure that tools correctly validate parameters and return expected structures.
"""
import sys
from pathlib import Path
from typing import Any
import jsonschema
import pytest
from jsonschema import ValidationError, validate

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from rmcp.tools.descriptive import frequency_table, outlier_detection, summary_stats
from rmcp.tools.fileops import data_info, filter_data, read_csv
from rmcp.tools.helpers import load_example, validate_data
from rmcp.tools.regression import (
    correlation_analysis,
    linear_model,
    logistic_regression,
)
from rmcp.tools.statistical_tests import anova, chi_square_test, normality_test, t_test
from rmcp.tools.visualization import correlation_heatmap, histogram, scatter_plot


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
    """Test chi_square_test input schema validation with oneOf."""

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
        """Test that independence test requires y variable."""
        invalid_input = {
            "data": {"var1": ["A", "B"]},
            "test_type": "independence",
            "x": "var1",
            # Missing "y" parameter required for independence
        }
        schema = chi_square_test._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        # The oneOf validation catches that this doesn't match any schema
        assert "was expected" in str(
            exc_info.value
        ) or "'y' is a required property" in str(exc_info.value)


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


class TestDescriptiveSchemaValidation:
    """Test descriptive statistics schema validation."""

    def test_summary_stats_valid_input(self):
        """Test valid summary statistics input."""
        valid_input = {
            "data": {"values": [1, 2, 3, 4, 5], "group": ["A", "A", "B", "B", "B"]},
            "variables": ["values"],
            "group_by": "group",
            "percentiles": [0.25, 0.5, 0.75],
        }
        schema = summary_stats._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_outlier_detection_valid_input(self):
        """Test valid outlier detection input."""
        valid_input = {
            "data": {"values": [1, 2, 3, 4, 100]},  # 100 is an outlier
            "variable": "values",
            "method": "iqr",
            "threshold": 3.0,
        }
        schema = outlier_detection._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_outlier_detection_invalid_method(self):
        """Test invalid outlier detection method."""
        invalid_input = {
            "data": {"values": [1, 2, 3]},
            "variable": "values",
            "method": "invalid_method",  # Not in enum
        }
        schema = outlier_detection._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        assert "is not one of" in str(exc_info.value)


class TestVisualizationSchemaValidation:
    """Test visualization tool schema validation."""

    def test_scatter_plot_valid_input(self):
        """Test valid scatter plot input."""
        valid_input = {
            "data": {"x_vals": [1, 2, 3, 4], "y_vals": [2, 4, 6, 8]},
            "x": "x_vals",
            "y": "y_vals",
            "title": "Test Scatter Plot",
            "return_image": True,
            "width": 800,
            "height": 600,
        }
        schema = scatter_plot._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_histogram_valid_input(self):
        """Test valid histogram input."""
        valid_input = {
            "data": {"values": [1, 2, 2, 3, 3, 3, 4, 4, 5]},
            "variable": "values",
            "bins": 10,
            "return_image": True,
        }
        schema = histogram._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_histogram_invalid_bins(self):
        """Test invalid number of bins."""
        invalid_input = {
            "data": {"values": [1, 2, 3]},
            "variable": "values",
            "bins": 200,  # Exceeds maximum of 100
        }
        schema = histogram._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        assert "is greater than the maximum" in str(exc_info.value)


class TestFileOpsSchemaValidation:
    """Test file operations schema validation."""

    def test_read_csv_valid_input(self):
        """Test valid CSV read input."""
        valid_input = {
            "file_path": "/path/to/data.csv",
            "header": True,
            "separator": ",",
            "skip_rows": 0,
        }
        schema = read_csv._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_filter_data_valid_input(self):
        """Test valid data filtering input."""
        valid_input = {
            "data": {"age": [25, 30, 35, 40], "income": [50000, 60000, 70000, 80000]},
            "conditions": [
                {"variable": "age", "operator": ">", "value": 30},
                {"variable": "income", "operator": "<=", "value": 75000},
            ],
            "logic": "AND",
        }
        schema = filter_data._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)


class TestOutputShapeCompliance:
    """Test that tools return expected output shapes (mock tests)."""

    def test_t_test_output_structure(self):
        """Test t_test returns expected output structure."""
        # Verify the function signature and imports work
        assert callable(t_test)
        assert hasattr(t_test, "_mcp_tool_input_schema")
        assert t_test.__annotations__["return"] == dict[str, Any]

    def test_correlation_heatmap_schema_structure(self):
        """Test correlation heatmap has expected schema structure."""
        schema = correlation_heatmap._mcp_tool_input_schema
        # Verify required fields
        assert "data" in schema["required"]
        # Verify method enum
        method_enum = schema["properties"]["method"]["enum"]
        assert "pearson" in method_enum
        assert "spearman" in method_enum
        assert "kendall" in method_enum

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
