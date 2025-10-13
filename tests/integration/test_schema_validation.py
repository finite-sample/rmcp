#!/usr/bin/env python3
"""
Schema Validation Integration Tests for RMCP

Tests that verify actual R script output matches the declared output schemas
for all statistical tools. This ensures schema-R output consistency and
prevents runtime validation errors.

These tests execute real R scripts with sample data and validate the
JSON output against the tool's declared output schema.
"""

import asyncio
import sys
from pathlib import Path
from shutil import which
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from jsonschema import ValidationError, validate

# Add rmcp to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.core.context import Context, LifespanState
from rmcp.core.schemas import validate_schema
from rmcp.tools import (
    descriptive,
    fileops,
    helpers,
    machine_learning,
    regression,
    statistical_tests,
    timeseries,
    transforms,
    visualization,
)

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for schema validation tests"
)


class SchemaValidationError(Exception):
    """Custom exception for schema validation failures."""

    def __init__(self, tool_name: str, error_details: str):
        self.tool_name = tool_name
        self.error_details = error_details
        super().__init__(f"Schema validation failed for {tool_name}: {error_details}")


@pytest_asyncio.fixture
async def context():
    """Create a test context for tool execution."""
    lifespan_state = LifespanState()
    ctx = Context.create("test", "test_schema_validation", lifespan_state)
    yield ctx


class TestSchemaValidation:
    """
    Test actual R output against declared schemas for all tools.

    Integration tests that execute real R statistical tools with sample data
    and validate the JSON output against declared Python schemas. These tests
    catch schema drift where R scripts evolve but schemas aren't updated.

    Each test method:
    1. Executes a real statistical tool with meaningful sample data
    2. Validates JSON output structure against declared schema
    3. Performs semantic validation of statistical results
    4. Ensures type correctness and value constraints
    """

    # Sample datasets for testing different tool categories
    SAMPLE_DATA = {
        "regression": {
            "data": {
                "sales": [100, 150, 200, 250, 300, 350, 400],
                "advertising": [10, 15, 20, 25, 30, 35, 40],
                "price": [50, 48, 45, 42, 40, 38, 35],
            },
            "binary_outcome": {
                "outcome": [0, 1, 0, 1, 1, 0, 1],
                "predictor": [1.2, 2.1, 1.5, 2.8, 3.1, 1.8, 2.9],
            },
        },
        "timeseries": {
            "ts_data": [100, 102, 105, 103, 108, 110, 107, 112, 115, 118, 120, 125],
            "ts_with_trend": [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32],
        },
        "descriptive": {
            "numeric_data": {
                "values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "weights": [1, 1, 2, 2, 3, 3, 2, 2, 1, 1],
            },
            "categorical_data": {
                "category": ["A", "B", "A", "C", "B", "A", "C", "B", "A", "C"],
                "value": [10, 20, 15, 25, 30, 12, 28, 22, 18, 26],
            },
        },
        "statistical_tests": {
            "group1": [1.2, 1.5, 1.8, 2.1, 2.4],
            "group2": [2.1, 2.4, 2.7, 3.0, 3.3],
            "contingency": {
                "treatment": ["A", "A", "B", "B", "A", "B"],
                "outcome": [
                    "success",
                    "failure",
                    "success",
                    "success",
                    "failure",
                    "success",
                ],
            },
        },
        "machine_learning": {
            "features": {
                "feature1": [1.2, 2.8, 3.1, 4.7, 5.3, 6.9, 7.2, 8.5],
                "feature2": [2.3, 4.1, 6.7, 8.2, 10.8, 12.1, 14.6, 16.3],
                "feature3": [1.8, 3.2, 5.9, 7.4, 9.1, 11.7, 13.2, 15.6],
            },
            "target_numeric": [10.5, 20.2, 30.8, 40.1, 50.7, 60.3, 70.9, 80.4],
            "target_categorical": ["A", "B", "A", "B", "A", "B", "A", "B"],
        },
    }

    async def _validate_tool_output(
        self, tool_func, params: Dict[str, Any], context: Context
    ) -> Dict[str, Any]:
        """Execute tool and validate output against schema."""
        tool_name = tool_func._mcp_tool_name
        output_schema = tool_func._mcp_tool_output_schema

        if not output_schema:
            pytest.skip(f"Tool {tool_name} has no output schema defined")

        try:
            # Execute the tool
            result = await tool_func(context, params)

            # Remove formatting info before validation (as done in production)
            if isinstance(result, dict) and "_formatting" in result:
                result = {k: v for k, v in result.items() if k != "_formatting"}

            # Validate against schema
            validate_schema(result, output_schema, f"tool '{tool_name}' output")

            return result

        except ValidationError as e:
            raise SchemaValidationError(
                tool_name,
                f"Schema validation failed: {e.message} at path {e.absolute_path}",
            )
        except Exception as e:
            raise SchemaValidationError(tool_name, f"Tool execution failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_linear_model_schema(self, context):
        """
        Test linear regression output schema validation.

        Validates that the linear_model tool produces R output matching its
        declared schema, including coefficient dictionary structure, R-squared
        values within valid range (0-1), and all required statistical fields.
        Also verifies semantic correctness of statistical results.
        """
        params = {
            "data": self.SAMPLE_DATA["regression"]["data"],
            "formula": "sales ~ advertising + price",
        }

        result = await self._validate_tool_output(
            regression.linear_model, params, context
        )

        # Additional semantic validation
        assert isinstance(result["coefficients"], dict)
        assert len(result["coefficients"]) >= 2  # intercept + at least one predictor
        assert 0 <= result["r_squared"] <= 1
        assert result["n_obs"] == len(self.SAMPLE_DATA["regression"]["data"]["sales"])
        assert result["method"] == "lm"

    @pytest.mark.asyncio
    async def test_correlation_analysis_schema(self, context):
        """
        Test correlation analysis output schema validation.

        Validates that correlation_analysis tool produces properly structured
        correlation matrix output with correct variable names and symmetric
        correlation coefficients. Ensures matrix dimensions match input data.
        """
        params = {"data": self.SAMPLE_DATA["regression"]["data"], "method": "pearson"}

        result = await self._validate_tool_output(
            regression.correlation_analysis, params, context
        )

        # Additional semantic validation
        corr_matrix = result["correlation_matrix"]
        variables = result["variables"]
        assert len(variables) == len(self.SAMPLE_DATA["regression"]["data"])
        assert all(var in corr_matrix for var in variables)

    @pytest.mark.asyncio
    async def test_logistic_regression_schema(self, context):
        """
        Test logistic regression output schema validation.

        Validates that logistic_regression tool produces correct GLM output
        including odds ratios, McFadden's R-squared, and binary classification
        metrics. Ensures family and link function are properly reported.
        """
        params = {
            "data": self.SAMPLE_DATA["regression"]["binary_outcome"],
            "formula": "outcome ~ predictor",
            "family": "binomial",
        }

        result = await self._validate_tool_output(
            regression.logistic_regression, params, context
        )

        # Additional semantic validation
        assert result["family"] == "binomial"
        assert isinstance(result["coefficients"], dict)
        assert "odds_ratios" in result
        assert 0 <= result["mcfadden_r_squared"] <= 1

    @pytest.mark.asyncio
    async def test_arima_model_schema(self, context):
        """
        Test ARIMA model output schema validation.

        Validates that arima_model tool produces time series model output
        with correct coefficient structure, model order specification,
        and time series diagnostics matching the declared schema.
        """
        params = {
            "data": {"values": self.SAMPLE_DATA["timeseries"]["ts_data"]},
            "order": [1, 1, 1],
        }

        result = await self._validate_tool_output(
            timeseries.arima_model, params, context
        )

        # Additional semantic validation
        assert result["model_type"] == "ARIMA"
        assert len(result["order"]) == 3
        assert isinstance(result["coefficients"], dict)
        assert result["n_obs"] == len(self.SAMPLE_DATA["timeseries"]["ts_data"])

    @pytest.mark.asyncio
    async def test_summary_stats_schema(self, context):
        """
        Test summary statistics output schema validation.

        Validates that summary_stats tool produces descriptive statistics
        with correct numeric types (mean, sd, etc.) and observation counts
        matching the input data structure and declared schema.
        """
        params = {
            "data": self.SAMPLE_DATA["descriptive"]["numeric_data"],
            "variables": ["values"],
        }

        result = await self._validate_tool_output(
            descriptive.summary_stats, params, context
        )

        # Additional semantic validation
        stats = result["statistics"]["values"]
        assert isinstance(stats["mean"], (int, float))
        assert isinstance(stats["sd"], (int, float))
        assert stats["n"] == len(
            self.SAMPLE_DATA["descriptive"]["numeric_data"]["values"]
        )

    @pytest.mark.asyncio
    async def test_t_test_schema(self, context):
        """
        Test t-test output schema validation.

        Validates that t_test tool produces statistical test results with
        correct p-value range (0-1), test statistic types, and test type
        classification matching the declared schema structure.
        """
        # Create single dataset with grouping variable for t-test
        group1_data = self.SAMPLE_DATA["statistical_tests"]["group1"]
        group2_data = self.SAMPLE_DATA["statistical_tests"]["group2"]
        params = {
            "data": {
                "value": group1_data + group2_data,
                "group": ["group1"] * len(group1_data) + ["group2"] * len(group2_data),
            },
            "variable": "value",
            "group": "group",
        }

        result = await self._validate_tool_output(
            statistical_tests.t_test, params, context
        )

        # Additional semantic validation
        assert result["test_type"] in [
            "One-sample t-test",
            "Paired t-test",
            "Two-sample t-test (equal variances)",
            "Welch's t-test",
        ]
        assert 0 <= result["p_value"] <= 1
        assert isinstance(result["statistic"], (int, float))

    @pytest.mark.asyncio
    async def test_kmeans_clustering_schema(self, context):
        """
        Test k-means clustering output schema validation.

        Validates that kmeans_clustering tool produces clustering results
        with correct cluster assignment arrays, centroid structures, and
        k-value matching input parameters and declared schema.
        """
        params = {
            "data": self.SAMPLE_DATA["machine_learning"]["features"],
            "variables": ["feature1", "feature2"],  # Specify which variables to use
            "k": 2,
        }

        result = await self._validate_tool_output(
            machine_learning.kmeans_clustering, params, context
        )

        # Additional semantic validation
        assert result["k"] == 2
        assert len(result["cluster_assignments"]) == len(
            self.SAMPLE_DATA["machine_learning"]["features"]["feature1"]
        )
        assert len(result["cluster_centers"]) == 2

    @pytest.mark.asyncio
    async def test_data_standardization_schema(self, context):
        """
        Test data standardization output schema validation.

        Validates that standardize tool produces transformed data with
        correct column structure, maintained data dimensions, and proper
        standardization method reporting matching the declared schema.
        """
        params = {
            "data": self.SAMPLE_DATA["machine_learning"]["features"],
            "variables": ["feature1", "feature2"],
            "method": "z_score",
        }

        result = await self._validate_tool_output(
            transforms.standardize, params, context
        )

        # Additional semantic validation
        transformed_data = result["data"]
        assert "feature1" in transformed_data
        assert "feature2" in transformed_data
        assert len(transformed_data["feature1"]) == len(
            self.SAMPLE_DATA["machine_learning"]["features"]["feature1"]
        )

    @pytest.mark.asyncio
    async def test_load_example_schema(self, context):
        """
        Test example data loading output schema validation.

        Validates that load_example tool produces dataset output with
        correct data structure, metadata fields, and size specifications
        matching the requested parameters and declared schema.
        """
        params = {"dataset_name": "sales", "size": "small"}

        result = await self._validate_tool_output(helpers.load_example, params, context)

        # Additional semantic validation
        assert "data" in result
        assert "metadata" in result
        assert result["metadata"]["size"] == "small"
        assert isinstance(result["data"], dict)

    @pytest.mark.asyncio
    async def test_suggest_fix_schema(self, context):
        """
        Test error suggestion output schema validation.

        Validates that suggest_fix tool produces error analysis with
        correct error type classification, suggestion list structure,
        and diagnostic information matching the declared schema.
        """
        params = {"error_message": "there is no package called 'forecast'"}

        result = await self._validate_tool_output(helpers.suggest_fix, params, context)

        # Additional semantic validation
        assert result["error_type"] in [
            "missing_package",
            "syntax_error",
            "data_error",
            "statistical_error",
            "unknown_error",
        ]
        assert isinstance(result["suggestions"], list)
        assert len(result["suggestions"]) > 0


class TestSchemaConsistency:
    """
    Test schema consistency across tool definitions.

    Validates that all tool schemas follow consistent structural patterns
    and use valid JSON Schema types. Helps maintain schema quality and
    consistency across the entire statistical tool ecosystem.
    """

    def test_all_tools_have_consistent_schema_structure(self):
        """
        Verify all output schemas follow consistent structure.

        Checks that every tool's output schema has required fields (type,
        properties), follows object schema pattern, and declares required
        fields that actually exist in the properties definition.
        """
        tool_modules = [
            regression,
            descriptive,
            statistical_tests,
            timeseries,
            machine_learning,
            transforms,
            visualization,
            fileops,
            helpers,
        ]

        schema_issues = []

        for module in tool_modules:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    hasattr(attr, "_mcp_tool_output_schema")
                    and attr._mcp_tool_output_schema is not None
                ):

                    schema = attr._mcp_tool_output_schema
                    tool_name = attr._mcp_tool_name

                    # Check basic schema structure
                    if not isinstance(schema, dict):
                        schema_issues.append(f"{tool_name}: Schema is not a dict")
                        continue

                    if schema.get("type") != "object":
                        schema_issues.append(
                            f"{tool_name}: Root type should be 'object'"
                        )

                    if "properties" not in schema:
                        schema_issues.append(f"{tool_name}: Missing 'properties' field")
                        continue

                    # Check for required fields
                    properties = schema["properties"]
                    required = schema.get("required", [])

                    # Verify required fields exist in properties
                    for req_field in required:
                        if req_field not in properties:
                            schema_issues.append(
                                f"{tool_name}: Required field '{req_field}' not in properties"
                            )

        if schema_issues:
            pytest.fail(
                f"Schema consistency issues found:\n" + "\n".join(schema_issues)
            )

    def test_schema_field_types_are_valid(self):
        """
        Verify all schema field types are valid JSON Schema types.

        Recursively validates that all type declarations in tool schemas
        use only valid JSON Schema type names (string, number, integer,
        boolean, array, object, null) and proper union type syntax.
        """
        valid_types = {
            "string",
            "number",
            "integer",
            "boolean",
            "array",
            "object",
            "null",
        }

        tool_modules = [
            regression,
            descriptive,
            statistical_tests,
            timeseries,
            machine_learning,
            transforms,
            visualization,
            fileops,
            helpers,
        ]

        type_issues = []

        for module in tool_modules:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    hasattr(attr, "_mcp_tool_output_schema")
                    and attr._mcp_tool_output_schema is not None
                ):

                    schema = attr._mcp_tool_output_schema
                    tool_name = attr._mcp_tool_name

                    def check_types(obj, path=""):
                        if isinstance(obj, dict):
                            if "type" in obj:
                                schema_type = obj["type"]
                                if isinstance(schema_type, str):
                                    if schema_type not in valid_types:
                                        type_issues.append(
                                            f"{tool_name}{path}: Invalid type '{schema_type}'"
                                        )
                                elif isinstance(schema_type, list):
                                    for t in schema_type:
                                        if t not in valid_types:
                                            type_issues.append(
                                                f"{tool_name}{path}: Invalid type '{t}' in union"
                                            )

                            for key, value in obj.items():
                                check_types(value, f"{path}.{key}")
                        elif isinstance(obj, list):
                            for i, item in enumerate(obj):
                                check_types(item, f"{path}[{i}]")

                    check_types(schema)

        if type_issues:
            pytest.fail(f"Schema type issues found:\n" + "\n".join(type_issues))


# Utility functions for debugging schema validation failures


def analyze_schema_mismatch(
    actual_output: Dict[str, Any], expected_schema: Dict[str, Any]
) -> str:
    """
    Analyze and provide detailed information about schema mismatches.

    Debugging utility that examines actual tool output against expected schema
    and generates human-readable explanations of validation failures.

    Args:
        actual_output: Dictionary containing actual tool output
        expected_schema: JSON Schema definition for expected output

    Returns:
        Human-readable string describing specific mismatches found,
        or "No obvious issues detected" if no problems identified

    Example:
        >>> mismatch_info = analyze_schema_mismatch(
        ...     {"r_squared": "0.85"},  # string instead of number
        ...     {"properties": {"r_squared": {"type": "number"}}}
        ... )
        >>> print(mismatch_info)
        "Field 'r_squared': expected number, got string"
    """
    issues = []

    if expected_schema.get("type") == "object" and "properties" in expected_schema:
        required_fields = expected_schema.get("required", [])
        properties = expected_schema["properties"]

        # Check missing required fields
        missing_required = [f for f in required_fields if f not in actual_output]
        if missing_required:
            issues.append(f"Missing required fields: {missing_required}")

        # Check extra fields (if additionalProperties is False)
        if expected_schema.get("additionalProperties") is False:
            extra_fields = [f for f in actual_output.keys() if f not in properties]
            if extra_fields:
                issues.append(f"Extra fields not allowed: {extra_fields}")

        # Check field type mismatches
        for field, value in actual_output.items():
            if field in properties:
                expected_type = properties[field].get("type")
                actual_type = type(value).__name__

                # Map Python types to JSON Schema types
                type_mapping = {
                    "str": "string",
                    "int": "integer",
                    "float": "number",
                    "bool": "boolean",
                    "list": "array",
                    "dict": "object",
                    "NoneType": "null",
                }

                json_type = type_mapping.get(actual_type, actual_type)
                if expected_type and json_type != expected_type:
                    issues.append(
                        f"Field '{field}': expected {expected_type}, got {json_type}"
                    )

    return "; ".join(issues) if issues else "No obvious issues detected"


if __name__ == "__main__":
    # Run schema validation tests
    pytest.main([__file__, "-v"])
