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

    def test_frequency_table_valid_input(self):
        """Test valid frequency table input."""
        valid_input = {
            "data": {"category": ["A", "B", "A", "C", "B", "A"]},
            "variables": ["category"],  # Changed from 'variable' to 'variables'
        }
        schema = frequency_table._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)

    def test_summary_stats_with_grouping(self):
        """Test summary stats with grouping variable."""
        valid_input = {
            "data": {
                "values": [1, 2, 3, 4, 5, 6],
                "category": ["A", "A", "B", "B", "C", "C"],
            },
            "variables": ["values"],
            "group_by": "category",
        }
        schema = summary_stats._mcp_tool_input_schema
        validate(instance=valid_input, schema=schema)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])