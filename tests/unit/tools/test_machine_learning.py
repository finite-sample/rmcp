#!/usr/bin/env python3
"""
Schema validation unit tests for machine learning tools.
Tests input schema validation and output shape compliance without R execution.
"""
import sys
from pathlib import Path

import pytest
from jsonschema import validate

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from rmcp.tools.machine_learning import (
    decision_tree,
    kmeans_clustering,
    random_forest,
)


class TestMachineLearningSchemaValidation:
    """Test machine learning tool schema validation."""

    def test_decision_tree_flattened_schema(self):
        """Test that decision_tree's flattened schema validates properly."""
        input_schema = decision_tree._mcp_tool_input_schema
        output_schema = decision_tree._mcp_tool_output_schema

        # Verify the output schema performance field is flattened (no oneOf)
        assert "oneOf" not in str(output_schema)

        # Test valid classification input
        valid_classification = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": ["A", "B", "A"]},
            "formula": "y ~ x1 + x2",
            "method": "class",
        }
        validate(instance=valid_classification, schema=input_schema)

        # Test valid regression input
        valid_regression = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": [10, 20, 30]},
            "formula": "y ~ x1 + x2",
            "method": "anova",
        }
        validate(instance=valid_regression, schema=input_schema)

    def test_random_forest_flattened_schema(self):
        """Test that random_forest's flattened schema validates properly."""
        input_schema = random_forest._mcp_tool_input_schema
        output_schema = random_forest._mcp_tool_output_schema

        # Verify the output schema performance field is flattened (no oneOf)
        assert "oneOf" not in str(output_schema)

        # Test valid classification input
        valid_classification = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": ["A", "B", "A"]},
            "formula": "y ~ x1 + x2",
            "n_trees": 100,
            "mtry": 2,
        }
        validate(instance=valid_classification, schema=input_schema)

        # Test valid regression input
        valid_regression = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": [10, 20, 30]},
            "formula": "y ~ x1 + x2",
            "n_trees": 50,
        }
        validate(instance=valid_regression, schema=input_schema)

    def test_kmeans_clustering_schema(self):
        """Test k-means clustering schema validation."""
        schema = kmeans_clustering._mcp_tool_input_schema

        # Valid input
        valid_input = {
            "data": {
                "feature1": [1, 2, 3, 4, 5],
                "feature2": [2, 4, 6, 8, 10],
                "feature3": [1, 1, 2, 2, 3],
            },
            "variables": ["feature1", "feature2", "feature3"],
            "k": 3,
            "max_iter": 100,
            "nstart": 25,
        }
        validate(instance=valid_input, schema=schema)

        # Check k constraints
        assert schema["properties"]["k"]["minimum"] == 2
        assert schema["properties"]["k"]["maximum"] == 20

    def test_tools_maintain_backward_compatibility(self):
        """Test that modified tools still accept the same inputs as before."""
        # Decision tree - both classification and regression
        dt_class_input = {
            "data": {"x": [1, 2, 3], "y": ["A", "B", "A"]},
            "formula": "y ~ x",
            "method": "class",
        }
        validate(instance=dt_class_input, schema=decision_tree._mcp_tool_input_schema)

        # Random forest - with various parameters
        rf_input = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": [10, 20, 30]},
            "formula": "y ~ x1 + x2",
            "n_trees": 100,
            "mtry": 2,
            "min_node_size": 5,
        }
        validate(instance=rf_input, schema=random_forest._mcp_tool_input_schema)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
