#!/usr/bin/env python3
"""
Schema validation unit tests for descriptive statistics tools.
Tests input schema validation and output shape compliance without R execution.
"""
import sys
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from rmcp.tools.descriptive import frequency_table, outlier_detection, summary_stats


class TestDescriptiveSchemaValidation:
    """Test descriptive statistics schema validation."""

    def test_summary_stats_valid_input(self):
        """Test valid summary statistics input."""
        # Realistic employee satisfaction scores by department
        valid_input = {
            "data": {
                "satisfaction_score": [
                    8.2,
                    7.8,
                    8.5,
                    7.9,
                    8.1,
                    7.6,
                    8.3,
                    7.7,
                    8.0,
                    8.4,
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
            "variables": ["satisfaction_score"],
            "group_by": "department",
            "percentiles": [0.25, 0.5, 0.75],
        }
        schema = summary_stats._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_outlier_detection_valid_input(self):
        """Test valid outlier detection input."""
        # Realistic sales data with potential outlier (R-validated)
        valid_input = {
            "data": {
                "monthly_sales": [45000, 47000, 52000, 48000, 125000]
            },  # 125000 is potential outlier
            "variable": "monthly_sales",
            "method": "iqr",
            "threshold": 3.0,
        }
        schema = outlier_detection._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_outlier_detection_invalid_method(self):
        """Test invalid outlier detection method."""
        invalid_input = {
            "data": {"monthly_sales": [45000, 47000, 52000]},
            "variable": "monthly_sales",
            "method": "invalid_method",  # Not in enum
        }
        schema = outlier_detection._mcp_tool_input_schema
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)
        assert "is not one of" in str(exc_info.value)

    def test_frequency_table_valid_input(self):
        """Test valid frequency table input."""
        # Realistic customer segment frequency analysis
        valid_input = {
            "data": {
                "customer_segment": [
                    "Premium",
                    "Standard",
                    "Premium",
                    "Budget",
                    "Standard",
                    "Premium",
                    "Luxury",
                    "Standard",
                    "Budget",
                    "Premium",
                ]
            },
            "variables": ["customer_segment"],  # Changed from 'variable' to 'variables'
        }
        schema = frequency_table._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_summary_stats_with_grouping(self):
        """Test summary stats with grouping variable."""
        # Realistic employee performance scores by department
        valid_input = {
            "data": {
                "performance_score": [85, 88, 78, 82, 90, 87, 75, 79, 92, 89],
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
            "variables": ["performance_score"],
            "group_by": "department",
        }
        schema = summary_stats._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
