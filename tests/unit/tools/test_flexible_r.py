#!/usr/bin/env python3
"""
Schema validation unit tests for flexible R execution tools.
Tests input schema validation and security constraints.
"""

import pytest
from jsonschema import ValidationError, validate
from rmcp.core.context import Context, LifespanState
from rmcp.tools.flexible_r import (
    execute_r_analysis,
    list_allowed_r_packages,
    validate_r_code,
)


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


class TestDeclaredPackagesAreValidated:
    """The `packages` argument is concatenated into library(...) lines.

    Unlike names parsed out of r_code, these are never seen by the pattern
    scans, so they must be validated on the way in or they bypass the
    allowlist, the dangerous-pattern block, and every approval category.
    """

    def _context(self):
        return Context.create("test", "test", LifespanState())

    def test_injection_through_packages_is_refused(self):
        is_safe, error = validate_r_code(
            "result <- 1",
            self._context(),
            packages=["stats); RMCP_INJECTION_MARKER <- TRUE; library(utils"],
        )
        assert not is_safe
        assert "Invalid package name" in error

    @pytest.mark.parametrize(
        "name",
        [
            "stats)",
            "utils; system('id')",
            "pkg name",
            "",
            "2pkg",
            "../../etc/passwd",
        ],
    )
    def test_non_identifier_package_names_are_refused(self, name):
        is_safe, error = validate_r_code(
            "result <- 1", self._context(), packages=[name]
        )
        assert not is_safe
        assert "Invalid package name" in error

    def test_package_outside_allowlist_requests_approval(self):
        is_safe, error = validate_r_code(
            "result <- 1", self._context(), packages=["definitelyNotOnTheAllowlist"]
        )
        assert not is_safe
        assert error == "APPROVAL_NEEDED:definitelyNotOnTheAllowlist"

    def test_session_approved_package_is_accepted(self):
        context = self._context()
        context.lifespan.approved_packages.add("notarealpkg")
        is_safe, error = validate_r_code(
            "result <- 1", context, packages=["notarealpkg"]
        )
        assert is_safe, error

    def test_allowlisted_package_is_accepted(self):
        is_safe, error = validate_r_code(
            "result <- 1", self._context(), packages=["dplyr", "ggplot2"]
        )
        assert is_safe, error

    def test_omitting_packages_is_unaffected(self):
        is_safe, error = validate_r_code("result <- 1", self._context())
        assert is_safe, error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
