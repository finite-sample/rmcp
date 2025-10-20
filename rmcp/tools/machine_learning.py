"""
Machine learning tools for RMCP.
Clustering, classification trees, and ML capabilities.
"""

from typing import Any

from ..core.schemas import formula_schema, table_schema
from ..r_assets.loader import get_r_script
from ..r_integration import execute_r_script_async
from ..registries.tools import tool


@tool(
    name="kmeans_clustering",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "k": {"type": "integer", "minimum": 2, "maximum": 20},
            "max_iter": {"type": "integer", "minimum": 1, "default": 100},
            "nstart": {"type": "integer", "minimum": 1, "default": 25},
        },
        "required": ["data", "variables", "k"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "cluster_assignments": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Cluster assignment for each observation",
            },
            "cluster_centers": {
                "type": "object",
                "description": "Centroid coordinates for each cluster",
                "additionalProperties": {"type": "array", "items": {"type": "number"}},
            },
            "cluster_sizes": {
                "type": "object",
                "description": "Number of observations in each cluster",
                "additionalProperties": {"type": "integer"},
            },
            "within_ss": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Within-cluster sum of squares for each cluster",
            },
            "total_within_ss": {
                "type": "number",
                "description": "Total within-cluster sum of squares",
                "minimum": 0,
            },
            "between_ss": {
                "type": "number",
                "description": "Between-cluster sum of squares",
                "minimum": 0,
            },
            "total_ss": {
                "type": "number",
                "description": "Total sum of squares",
                "minimum": 0,
            },
            "variance_explained": {
                "type": "number",
                "description": "Percentage of variance explained by clustering",
                "minimum": 0,
                "maximum": 100,
            },
            "silhouette_score": {
                "type": "number",
                "description": "Average silhouette score (-1 to 1, higher is better)",
                "minimum": -1,
                "maximum": 1,
            },
            "k": {
                "type": "integer",
                "description": "Number of clusters",
                "minimum": 2,
                "maximum": 20,
            },
            "variables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Variables used for clustering",
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations clustered",
                "minimum": 1,
            },
            "converged": {
                "type": "boolean",
                "description": "Whether the algorithm converged",
            },
        },
        "required": [
            "cluster_assignments",
            "cluster_centers",
            "cluster_sizes",
            "within_ss",
            "total_within_ss",
            "between_ss",
            "total_ss",
            "variance_explained",
            "silhouette_score",
            "k",
            "variables",
            "n_obs",
            "converged",
        ],
        "additionalProperties": False,
    },
    description="Performs K-means clustering to partition data into k clusters based on feature similarity. Uses multiple random starts for optimal clustering and provides cluster assignments, centroids, within-cluster sum of squares, and silhouette analysis for cluster quality assessment. Use for customer segmentation, market research, data exploration, pattern recognition, or reducing data complexity by grouping similar observations.",
)
async def kmeans_clustering(context, params) -> dict[str, Any]:
    """Perform K-means clustering."""
    await context.info("Performing K-means clustering")

    r_script = get_r_script("machine_learning", "kmeans_clustering")
    try:
        result = await execute_r_script_async(r_script, params, context)
        await context.info("K-means clustering completed successfully")
        return result
    except Exception as e:
        await context.error("K-means clustering failed", error=str(e))
        raise


@tool(
    name="decision_tree",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": formula_schema(),
            "type": {
                "type": "string",
                "enum": ["classification", "regression"],
                "default": "classification",
            },
            "min_split": {"type": "integer", "minimum": 1, "default": 20},
            "max_depth": {"type": "integer", "minimum": 1, "default": 30},
        },
        "required": ["data", "formula"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "tree_type": {
                "type": "string",
                "enum": ["classification", "regression"],
                "description": "Type of decision tree",
            },
            "performance": {
                "type": "object",
                "description": "Model performance metrics",
                "properties": {
                    "accuracy": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Classification accuracy (for classification trees)",
                    },
                    "confusion_matrix": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "Confusion matrix (for classification trees)",
                    },
                    "mse": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Mean squared error (for regression trees)",
                    },
                    "rmse": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Root mean squared error (for regression trees)",
                    },
                    "r_squared": {
                        "type": "number",
                        "maximum": 1,
                        "description": "R-squared value (for regression trees)",
                    },
                },
                "additionalProperties": False,
            },
            "variable_importance": {
                "type": "object",
                "description": "Relative importance of variables",
                "additionalProperties": {"type": "number"},
            },
            "predictions": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Model predictions for training data",
            },
            "n_nodes": {
                "type": "integer",
                "description": "Number of nodes in the tree",
                "minimum": 1,
            },
            "n_obs": {
                "type": "integer",
                "description": "Number of observations",
                "minimum": 1,
            },
            "formula": {"type": "string", "description": "Model formula used"},
            "tree_complexity": {
                "type": "number",
                "description": "Complexity parameter of the tree",
                "minimum": 0,
            },
        },
        "required": [
            "tree_type",
            "performance",
            "variable_importance",
            "predictions",
            "n_nodes",
            "n_obs",
            "formula",
            "tree_complexity",
        ],
        "additionalProperties": False,
    },
    description="Builds decision tree models for classification (categorical outcomes) or regression (continuous outcomes) using recursive binary splitting. Provides tree structure, variable importance rankings, prediction rules, and cross-validation accuracy. Trees are interpretable and handle mixed data types naturally. Use for rule-based modeling, feature selection, understanding decision processes, or when interpretability is more important than maximum accuracy.",
)
async def decision_tree(context, params) -> dict[str, Any]:
    """Build decision tree model."""
    await context.info("Building decision tree")

    r_script = get_r_script("machine_learning", "decision_tree")
    try:
        result = await execute_r_script_async(r_script, params, context)
        await context.info("Decision tree built successfully")
        return result
    except Exception as e:
        await context.error("Decision tree building failed", error=str(e))
        raise


@tool(
    name="random_forest",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "formula": formula_schema(),
            "n_trees": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
                "default": 500,
            },
            "mtry": {"type": "integer", "minimum": 1},
            "importance": {"type": "boolean", "default": True},
        },
        "required": ["data", "formula"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "problem_type": {
                "type": "string",
                "enum": ["classification", "regression"],
                "description": "Type of machine learning problem",
            },
            "performance": {
                "type": "object",
                "description": "Model performance metrics",
                "properties": {
                    "oob_error_rate": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Out-of-bag error rate (for classification)",
                    },
                    "confusion_matrix": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "Confusion matrix (for classification)",
                    },
                    "class_error": {
                        "type": "object",
                        "description": "Error rate by class (for classification)",
                        "additionalProperties": {"type": "number"},
                    },
                    "mse": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Mean squared error (for regression)",
                    },
                    "rmse": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Root mean squared error (for regression)",
                    },
                    "variance_explained": {
                        "type": "number",
                        "description": "Percentage of variance explained (for regression)",
                        "maximum": 100,
                    },
                },
                "additionalProperties": False,
            },
            "variable_importance": {
                "type": ["object", "null"],
                "description": "Variable importance measures (if calculated)",
                "additionalProperties": {"type": "number"},
            },
            "n_trees": {
                "type": "integer",
                "description": "Number of trees in the forest",
                "minimum": 1,
                "maximum": 1000,
            },
            "mtry": {
                "type": "integer",
                "description": "Number of variables randomly sampled at each split",
                "minimum": 1,
            },
            "oob_error": {
                "type": "number",
                "description": "Out-of-bag error estimate",
                "minimum": 0,
            },
            "formula": {"type": "string", "description": "Model formula used"},
            "n_obs": {
                "type": "integer",
                "description": "Number of observations",
                "minimum": 1,
            },
        },
        "required": [
            "problem_type",
            "performance",
            "n_trees",
            "mtry",
            "oob_error",
            "formula",
            "n_obs",
        ],
        "additionalProperties": False,
    },
    description="Constructs Random Forest ensemble models combining multiple decision trees with bootstrap sampling and random feature selection. Provides predictions, variable importance rankings, out-of-bag error estimates, and partial dependence plots. More accurate and robust than single trees while maintaining interpretability through variable importance. Use for high-accuracy prediction, feature selection, handling missing data, or non-linear relationships.",
)
async def random_forest(context, params) -> dict[str, Any]:
    """Build Random Forest model."""
    await context.info("Building Random Forest model")

    r_script = get_r_script("machine_learning", "random_forest")
    try:
        result = await execute_r_script_async(r_script, params, context)
        await context.info("Random Forest model built successfully")
        return result
    except Exception as e:
        await context.error("Random Forest building failed", error=str(e))
        raise
