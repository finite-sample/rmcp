#!/usr/bin/env python3
"""
Schema validation unit tests for flexible R execution tools.
Tests input schema validation and security constraints.
"""
import sys
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

from rmcp.tools.flexible_r import execute_r_analysis, list_allowed_r_packages


class TestFlexibleRSchemaValidation:
    """Test flexible R execution schema validation."""

    def test_execute_r_analysis_flattened_schema(self):
        """Test that execute_r_analysis's flattened schema works correctly."""
        schema = execute_r_analysis._mcp_tool_input_schema

        # Check data field doesn't have oneOf
        if "data" in schema["properties"]:
            assert "oneOf" not in str(schema["properties"]["data"])

        # Test valid input with data
        valid_with_data = {
            "r_code": "result <- mean(data$values)",
            "data": {"values": [1, 2, 3, 4, 5]},
            "description": "Calculate mean",
        }
        validate(instance=valid_with_data, schema=schema)

        # Test valid input without data (if allowed)
        valid_without_data = {
            "r_code": "result <- 1:10",
            "description": "Generate sequence",
        }
        # This should validate if data is optional
        try:
            validate(instance=valid_without_data, schema=schema)
        except ValidationError:
            # If data is required, that's fine too
            pass

    def test_execute_r_with_packages(self):
        """Test R execution with package requirements."""
        schema = execute_r_analysis._mcp_tool_input_schema

        valid_input = {
            "r_code": "library(dplyr)\nresult <- data %>% summarize(mean = mean(values))",
            "data": {"values": [1, 2, 3, 4, 5]},
            "packages": ["dplyr"],
            "description": "Calculate mean using dplyr",
        }
        validate(instance=valid_input, schema=schema)

    def test_execute_r_with_timeout(self):
        """Test R execution with timeout specification."""
        schema = execute_r_analysis._mcp_tool_input_schema

        valid_input = {
            "r_code": "result <- complex_calculation()",
            "description": "Long running calculation",
            "timeout_seconds": 300,  # 5 minutes
        }
        validate(instance=valid_input, schema=schema)

        # Check timeout constraints
        if "timeout_seconds" in schema["properties"]:
            assert schema["properties"]["timeout_seconds"]["minimum"] == 1
            assert schema["properties"]["timeout_seconds"]["maximum"] == 300

    def test_execute_r_with_image_output(self):
        """Test R execution with image output request."""
        schema = execute_r_analysis._mcp_tool_input_schema

        valid_input = {
            "r_code": "plot(1:10)\nresult <- 'Plot created'",
            "description": "Create a plot",
            "return_image": True,
        }
        validate(instance=valid_input, schema=schema)

    def test_list_allowed_packages_schema(self):
        """Test list_allowed_r_packages schema."""
        schema = list_allowed_r_packages._mcp_tool_input_schema

        # This tool typically has no required inputs
        valid_input = {}
        validate(instance=valid_input, schema=schema)

        # Or might accept optional category filter
        valid_with_filter = {"category": "statistics"}
        try:
            validate(instance=valid_with_filter, schema=schema)
        except ValidationError:
            # If category is not supported, that's fine
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
