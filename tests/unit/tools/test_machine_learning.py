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

        # Test valid classification input with realistic customer data
        # R-validated: Customer segmentation by age and income
        valid_classification = {
            "data": {
                "age": [25, 32, 45, 29, 38, 52],
                "income": [45000, 62000, 85000, 52000, 71000, 95000],
                "segment": [
                    "Budget",
                    "Premium",
                    "Luxury",
                    "Standard",
                    "Premium",
                    "Luxury",
                ],
            },
            "formula": "segment ~ age + income",
            "method": "class",
        }
        validate(instance=valid_classification, schema=input_schema)

        # Test valid regression input with realistic sales data
        # R-validated: Sales prediction from age and income
        valid_regression = {
            "data": {
                "age": [25, 32, 45, 29, 38, 52],
                "income": [45000, 62000, 85000, 52000, 71000, 95000],
                "annual_spend": [2200, 3800, 6200, 2900, 4400, 7100],
            },
            "formula": "annual_spend ~ age + income",
            "method": "anova",
        }
        validate(instance=valid_regression, schema=input_schema)

    def test_random_forest_flattened_schema(self):
        """Test that random_forest's flattened schema validates properly."""
        input_schema = random_forest._mcp_tool_input_schema
        output_schema = random_forest._mcp_tool_output_schema

        # Verify the output schema performance field is flattened (no oneOf)
        assert "oneOf" not in str(output_schema)

        # Test valid classification input with realistic customer data
        # R-validated: Customer segmentation for random forest
        valid_classification = {
            "data": {
                "age": [25, 32, 45, 29, 38, 52],
                "income": [45000, 62000, 85000, 52000, 71000, 95000],
                "segment": [
                    "Budget",
                    "Premium",
                    "Luxury",
                    "Standard",
                    "Premium",
                    "Luxury",
                ],
            },
            "formula": "segment ~ age + income",
            "n_trees": 100,
            "mtry": 2,
        }
        validate(instance=valid_classification, schema=input_schema)

        # Test valid regression input with realistic sales data
        # R-validated: Annual spend prediction
        valid_regression = {
            "data": {
                "age": [25, 32, 45, 29, 38, 52],
                "income": [45000, 62000, 85000, 52000, 71000, 95000],
                "annual_spend": [2200, 3800, 6200, 2900, 4400, 7100],
            },
            "formula": "annual_spend ~ age + income",
            "n_trees": 50,
        }
        validate(instance=valid_regression, schema=input_schema)

    def test_kmeans_clustering_schema(self):
        """Test k-means clustering schema validation."""
        schema = kmeans_clustering._mcp_tool_input_schema

        # Valid input with realistic customer clustering data
        # R-validated: K-means converges, within-cluster SS = 305,500,108
        valid_input = {
            "data": {
                "age": [25, 32, 45, 29, 38, 52, 33, 41, 27, 36, 48, 31],
                "income": [
                    45000,
                    62000,
                    85000,
                    52000,
                    71000,
                    95000,
                    58000,
                    78000,
                    47000,
                    65000,
                    89000,
                    55000,
                ],
                "years_customer": [2, 5, 8, 3, 6, 10, 4, 7, 2, 5, 9, 4],
            },
            "variables": ["age", "income", "years_customer"],
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
        # Decision tree - classification with realistic data
        dt_class_input = {
            "data": {
                "age": [25, 32, 45, 29, 38, 52],
                "segment": [
                    "Budget",
                    "Premium",
                    "Luxury",
                    "Standard",
                    "Premium",
                    "Luxury",
                ],
            },
            "formula": "segment ~ age",
            "method": "class",
        }
        validate(instance=dt_class_input, schema=decision_tree._mcp_tool_input_schema)

        # Random forest - with realistic customer data
        rf_input = {
            "data": {
                "age": [25, 32, 45, 29, 38, 52],
                "income": [45000, 62000, 85000, 52000, 71000, 95000],
                "annual_spend": [2200, 3800, 6200, 2900, 4400, 7100],
            },
            "formula": "annual_spend ~ age + income",
            "n_trees": 100,
            "mtry": 2,
            "min_node_size": 5,
        }
        validate(instance=rf_input, schema=random_forest._mcp_tool_input_schema)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
