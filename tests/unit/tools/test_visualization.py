#!/usr/bin/env python3
"""
Schema validation unit tests for visualization tools.
Tests input schema validation and output shape compliance without R execution.
"""
import sys
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from rmcp.tools.visualization import (
    boxplot,
    correlation_heatmap,
    histogram,
    regression_plot,
    scatter_plot,
    time_series_plot,
)


class TestVisualizationSchemaValidation:
    """Test visualization tool schema validation."""

    def test_scatter_plot_valid_input(self):
        """Test valid scatter plot input."""
        # Realistic sales vs marketing spend visualization
        valid_input = {
            "data": {
                "marketing_spend": [10, 12, 11, 14, 16, 15, 18, 20],
                "sales_revenue": [120, 135, 128, 142, 156, 148, 160, 175],
            },
            "x": "marketing_spend",
            "y": "sales_revenue",
            "title": "Sales vs Marketing Spend",
            "return_image": True,
            "width": 800,
            "height": 600,
        }
        schema = scatter_plot._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_histogram_valid_input(self):
        """Test valid histogram input."""
        # Realistic customer satisfaction scores distribution
        valid_input = {
            "data": {
                "satisfaction_scores": [
                    7.8,
                    8.2,
                    8.2,
                    8.5,
                    8.5,
                    8.5,
                    7.9,
                    7.9,
                    8.1,
                    8.3,
                    7.7,
                    8.4,
                ]
            },
            "variable": "satisfaction_scores",
            "bins": 10,
            "return_image": True,
        }
        schema = histogram._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_histogram_invalid_bins(self):
        """Test invalid number of bins."""
        invalid_input = {
            "data": {"satisfaction_scores": [7.8, 8.2, 8.5]},
            "variable": "satisfaction_scores",
            "bins": 200,  # Exceeds maximum of 100
        }
        schema = histogram._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        assert "is greater than the maximum" in str(exc_info.value)

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

    def test_boxplot_valid_input(self):
        """Test valid boxplot input."""
        valid_input = {
            "data": {
                "values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "group": ["A", "A", "A", "B", "B", "B", "C", "C", "C", "C"],
            },
            "variable": "values",
            "group_by": "group",
            "title": "Test Boxplot",
        }
        schema = boxplot._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_time_series_plot_valid_input(self):
        """Test valid time series plot input."""
        valid_input = {
            "data": {
                "time": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "values": [100, 110, 105],
            },
            "time_variable": "time",
            "value_variables": ["values"],
            "title": "Test Time Series",
        }
        schema = time_series_plot._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_regression_plot_valid_input(self):
        """Test valid regression plot input."""
        valid_input = {
            "data": {
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 5, 8, 10],
            },
            "formula": "y ~ x",  # regression_plot requires formula not x and y
        }
        schema = regression_plot._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
