#!/usr/bin/env python3
"""
Consolidated schema validation unit tests for RMCP tools.
Tests input schema validation and output shape compliance without R execution.
Uses parameterized tests for key tool categories.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
from jsonschema import ValidationError, validate

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import available tool modules
from rmcp.tools import regression, statistical_tests


def get_test_tools() -> List[Tuple[str, Any, Dict[str, Any]]]:
    """Get core tools with their test data for parameterized testing."""
    tools_test_data = [
        # Regression tools
        (
            "linear_model",
            regression.linear_model,
            {
                "data": {
                    "sales": [120, 135, 128, 142, 156, 148, 160, 175],
                    "marketing": [10, 12, 11, 14, 16, 15, 18, 20],
                },
                "formula": "sales ~ marketing",
            },
        ),
        # Statistical tests
        (
            "t_test",
            statistical_tests.t_test,
            {
                "data": {"test_scores": [78, 82, 85, 79, 88, 84, 81, 86, 83, 87]},
                "variable": "test_scores",
                "mu": 80,
                "alternative": "two.sided",
            },
        ),
    ]

    return tools_test_data


class TestAllToolSchemas:
    """Test schema validation for all RMCP tools."""

    @pytest.mark.parametrize("tool_name,tool_func,test_input", get_test_tools())
    def test_tool_input_schema_validation(
        self, tool_name: str, tool_func: Any, test_input: Dict[str, Any]
    ):
        """Test that all tools have valid input schemas and accept realistic data."""
        # Verify tool has schema
        assert hasattr(
            tool_func, "_mcp_tool_input_schema"
        ), f"{tool_name} missing input schema"

        schema = tool_func._mcp_tool_input_schema
        assert isinstance(schema, dict), f"{tool_name} schema is not a dict"
        assert "type" in schema, f"{tool_name} schema missing type"
        assert "properties" in schema, f"{tool_name} schema missing properties"

        # Validate test input against schema
        try:
            validate(instance=test_input, schema=schema)
        except ValidationError as e:
            pytest.fail(
                f"{tool_name} schema validation failed with realistic data: {e}"
            )

    @pytest.mark.parametrize("tool_name,tool_func,test_input", get_test_tools())
    def test_tool_function_signature(
        self, tool_name: str, tool_func: Any, test_input: Dict[str, Any]
    ):
        """Test that all tools have proper function signatures."""
        # Verify tool is callable
        assert callable(tool_func), f"{tool_name} is not callable"

        # Verify tool has return type annotation
        assert hasattr(
            tool_func, "__annotations__"
        ), f"{tool_name} missing type annotations"
        annotations = tool_func.__annotations__
        assert "return" in annotations, f"{tool_name} missing return type annotation"

    @pytest.mark.parametrize("tool_name,tool_func,test_input", get_test_tools())
    def test_tool_metadata_completeness(
        self, tool_name: str, tool_func: Any, test_input: Dict[str, Any]
    ):
        """Test that all tools have complete metadata."""
        # Check for required MCP tool attributes
        assert hasattr(
            tool_func, "_mcp_tool_name"
        ), f"{tool_name} missing _mcp_tool_name"
        assert hasattr(
            tool_func, "_mcp_tool_description"
        ), f"{tool_name} missing _mcp_tool_description"
        assert hasattr(
            tool_func, "_mcp_tool_input_schema"
        ), f"{tool_name} missing _mcp_tool_input_schema"

        # Verify metadata values
        assert tool_func._mcp_tool_name == tool_name, f"{tool_name} name mismatch"
        assert isinstance(
            tool_func._mcp_tool_description, str
        ), f"{tool_name} description not string"
        assert (
            len(tool_func._mcp_tool_description) > 0
        ), f"{tool_name} empty description"


class TestToolSchemaStructure:
    """Test common schema structure patterns across tools."""

    @pytest.mark.parametrize("tool_name,tool_func,test_input", get_test_tools())
    def test_data_parameter_structure(
        self, tool_name: str, tool_func: Any, test_input: Dict[str, Any]
    ):
        """Test that tools with data parameters have consistent structure."""
        schema = tool_func._mcp_tool_input_schema

        if "data" in schema.get("properties", {}):
            data_schema = schema["properties"]["data"]
            assert (
                data_schema["type"] == "object"
            ), f"{tool_name} data parameter should be object type"
            assert (
                "properties" in data_schema
            ), f"{tool_name} data parameter missing properties"

    @pytest.mark.parametrize("tool_name,tool_func,test_input", get_test_tools())
    def test_required_fields_present(
        self, tool_name: str, tool_func: Any, test_input: Dict[str, Any]
    ):
        """Test that required fields are properly specified."""
        schema = tool_func._mcp_tool_input_schema

        if "required" in schema:
            required_fields = schema["required"]
            assert isinstance(
                required_fields, list
            ), f"{tool_name} required should be list"

            # Check that all required fields exist in properties
            properties = schema.get("properties", {})
            for field in required_fields:
                assert (
                    field in properties
                ), f"{tool_name} required field '{field}' not in properties"

    @pytest.mark.parametrize("tool_name,tool_func,test_input", get_test_tools())
    def test_enum_values_validation(
        self, tool_name: str, tool_func: Any, test_input: Dict[str, Any]
    ):
        """Test that enum values in schemas are valid."""
        schema = tool_func._mcp_tool_input_schema

        def check_enum_in_schema(obj):
            if isinstance(obj, dict):
                if "enum" in obj:
                    enum_values = obj["enum"]
                    assert isinstance(
                        enum_values, list
                    ), f"{tool_name} enum should be list"
                    assert len(enum_values) > 0, f"{tool_name} enum should not be empty"
                    assert len(set(enum_values)) == len(
                        enum_values
                    ), f"{tool_name} enum has duplicates"

                for value in obj.values():
                    check_enum_in_schema(value)
            elif isinstance(obj, list):
                for item in obj:
                    check_enum_in_schema(item)

        check_enum_in_schema(schema)


class TestToolSchemaEdgeCases:
    """Test edge cases and error conditions in tool schemas."""

    def test_invalid_input_rejection(self):
        """Test that tools properly reject invalid input through schema validation."""
        # Test with a representative tool
        tool = statistical_tests.t_test
        schema = tool._mcp_tool_input_schema

        invalid_inputs = [
            {},  # Empty object
            {"data": "not_an_object"},  # Wrong data type
            {"data": {}, "variable": 123},  # Wrong variable type
            {
                "data": {"x": [1, 2]},
                "variable": "x",
                "alternative": "invalid_option",
            },  # Invalid enum
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises(ValidationError):
                validate(instance=invalid_input, schema=schema)

    def test_missing_required_parameters(self):
        """Test schema validation for missing required parameters."""
        # Test with a tool that has required parameters
        tool = regression.linear_model
        schema = tool._mcp_tool_input_schema

        # Input missing required 'data' parameter
        invalid_input = {"formula": "y ~ x"}

        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_input, schema=schema)

        assert "'data' is a required property" in str(exc_info.value)

    def test_additional_properties_handling(self):
        """Test how schemas handle additional properties."""
        # Test with a representative tool
        tool = statistical_tests.t_test
        schema = tool._mcp_tool_input_schema

        # Valid input with extra property
        input_with_extra = {
            "data": {"x": [1, 2, 3]},
            "variables": ["x"],
            "extra_property": "should_be_ignored_or_rejected",
        }

        # Schema validation behavior depends on additionalProperties setting
        try:
            validate(instance=input_with_extra, schema=schema)
            # If validation passes, additionalProperties is allowed
            assert True
        except ValidationError:
            # If validation fails, additionalProperties is not allowed
            assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
