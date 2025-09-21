"""
Machine learning tools for RMCP.

Clustering, classification trees, and ML capabilities.
"""

from typing import Any

from ..core.schemas import formula_schema, table_schema
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
    description="K-means clustering analysis with cluster validation",
)
async def kmeans_clustering(context, params) -> dict[str, Any]:
    """Perform K-means clustering."""

    await context.info("Performing K-means clustering")

    r_script = """
    
    data <- as.data.frame(args$data)
    variables <- args$variables
    k <- args$k
    max_iter <- args$max_iter %||% 100
    nstart <- args$nstart %||% 25
    
    # Select and prepare data
    rmcp_progress("Preparing data for clustering")
    cluster_data <- data[, variables, drop = FALSE]
    cluster_data <- na.omit(cluster_data)
    
    # Scale variables for clustering
    rmcp_progress("Scaling variables for clustering")
    scaled_data <- scale(cluster_data)
    
    # Perform k-means
    rmcp_progress("Running k-means clustering", 0, 100)
    set.seed(123)  # For reproducibility
    kmeans_result <- kmeans(scaled_data, centers = k, iter.max = max_iter, nstart = nstart)
    rmcp_progress("K-means clustering completed", 100, 100)
    
    # Calculate cluster statistics
    cluster_centers <- kmeans_result$centers
    cluster_assignments <- kmeans_result$cluster
    
    # Within-cluster sum of squares
    wss <- kmeans_result$withinss
    total_wss <- kmeans_result$tot.withinss
    between_ss <- kmeans_result$betweenss
    total_ss <- kmeans_result$totss
    
    # Cluster sizes
    cluster_sizes <- table(cluster_assignments)
    
    # Silhouette analysis 
    library(cluster)
    sil <- silhouette(cluster_assignments, dist(scaled_data))
    silhouette_score <- mean(sil[, 3])
    
    result <- list(
        cluster_assignments = cluster_assignments,
        cluster_centers = as.list(as.data.frame(cluster_centers)),
        cluster_sizes = as.list(cluster_sizes),
        within_ss = wss,
        total_within_ss = total_wss,
        between_ss = between_ss,
        total_ss = total_ss,
        variance_explained = between_ss / total_ss * 100,
        silhouette_score = silhouette_score,
        k = k,
        variables = variables,
        n_obs = nrow(cluster_data),
        converged = kmeans_result$iter < max_iter
    )
    """

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
                "oneOf": [
                    {
                        "properties": {
                            "accuracy": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "Classification accuracy",
                            },
                            "confusion_matrix": {
                                "type": "array",
                                "items": {"type": "array", "items": {"type": "number"}},
                                "description": "Confusion matrix for classification",
                            },
                        },
                        "required": ["accuracy", "confusion_matrix"],
                    },
                    {
                        "properties": {
                            "mse": {
                                "type": "number",
                                "minimum": 0,
                                "description": "Mean squared error",
                            },
                            "rmse": {
                                "type": "number",
                                "minimum": 0,
                                "description": "Root mean squared error",
                            },
                            "r_squared": {
                                "type": "number",
                                "maximum": 1,
                                "description": "R-squared value",
                            },
                        },
                        "required": ["mse", "rmse", "r_squared"],
                    },
                ],
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
    description="Decision tree classification and regression",
)
async def decision_tree(context, params) -> dict[str, Any]:
    """Build decision tree model."""

    await context.info("Building decision tree")

    r_script = """
    library(rpart)
    
    data <- as.data.frame(args$data)
    formula <- as.formula(args$formula)
    tree_type <- args$type %||% "classification"
    min_split <- args$min_split %||% 20
    max_depth <- args$max_depth %||% 30
    
    # Set method based on type
    if (tree_type == "classification") {
        method <- "class"
    } else {
        method <- "anova"
    }
    
    # Build tree
    tree_model <- rpart(formula, data = data, method = method,
                       control = rpart.control(minsplit = min_split, maxdepth = max_depth))
    
    # Get predictions
    predictions <- predict(tree_model, type = if (method == "class") "class" else "vector")
    
    # Calculate performance metrics
    if (tree_type == "classification") {
        # Classification metrics
        response_var <- all.vars(formula)[1]
        actual <- data[[response_var]]
        confusion_matrix <- table(Predicted = predictions, Actual = actual)
        accuracy <- sum(diag(confusion_matrix)) / sum(confusion_matrix)
        
        performance <- list(
            accuracy = accuracy,
            confusion_matrix = as.matrix(confusion_matrix)
        )
    } else {
        # Regression metrics
        response_var <- all.vars(formula)[1]
        actual <- data[[response_var]]
        mse <- mean((predictions - actual)^2, na.rm = TRUE)
        rmse <- sqrt(mse)
        r_squared <- 1 - sum((actual - predictions)^2, na.rm = TRUE) / sum((actual - mean(actual, na.rm = TRUE))^2, na.rm = TRUE)
        
        performance <- list(
            mse = mse,
            rmse = rmse,
            r_squared = r_squared
        )
    }
    
    # Variable importance
    var_importance <- tree_model$variable.importance
    
    result <- list(
        tree_type = tree_type,
        performance = performance,
        variable_importance = as.list(var_importance),
        predictions = as.numeric(predictions),
        n_nodes = nrow(tree_model$frame),
        n_obs = nrow(data),
        formula = deparse(formula),
        tree_complexity = tree_model$cptable[nrow(tree_model$cptable), "CP"]
    )
    """

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
                "oneOf": [
                    {
                        "properties": {
                            "oob_error_rate": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "Out-of-bag error rate",
                            },
                            "confusion_matrix": {
                                "type": "array",
                                "items": {"type": "array", "items": {"type": "number"}},
                                "description": "Confusion matrix for classification",
                            },
                            "class_error": {
                                "type": "object",
                                "description": "Error rate by class",
                                "additionalProperties": {"type": "number"},
                            },
                        },
                        "required": [
                            "oob_error_rate",
                            "confusion_matrix",
                            "class_error",
                        ],
                    },
                    {
                        "properties": {
                            "mse": {
                                "type": "number",
                                "minimum": 0,
                                "description": "Mean squared error",
                            },
                            "rmse": {
                                "type": "number",
                                "minimum": 0,
                                "description": "Root mean squared error",
                            },
                            "variance_explained": {
                                "type": "number",
                                "description": "Percentage of variance explained",
                                "maximum": 100,
                            },
                        },
                        "required": ["mse", "rmse", "variance_explained"],
                    },
                ],
            },
            "variable_importance": {
                "type": ["object", "null"],
                "description": "Variable importance measures (if calculated)",
                "additionalProperties": {"type": "array", "items": {"type": "number"}},
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
    description="Random Forest ensemble model for classification and regression",
)
async def random_forest(context, params) -> dict[str, Any]:
    """Build Random Forest model."""

    await context.info("Building Random Forest model")

    r_script = """
    library(randomForest)
    
    data <- as.data.frame(args$data)
    formula <- as.formula(args$formula)
    n_trees <- args$n_trees %||% 500
    mtry_val <- args$mtry
    importance <- args$importance %||% TRUE
    
    # Determine problem type
    rmcp_progress("Analyzing data structure")
    response_var <- all.vars(formula)[1]
    if (is.factor(data[[response_var]]) || is.character(data[[response_var]])) {
        # Convert to factor if character
        if (is.character(data[[response_var]])) {
            data[[response_var]] <- as.factor(data[[response_var]])
        }
        problem_type <- "classification"
    } else {
        problem_type <- "regression"
    }
    
    # Set default mtry if not provided
    rmcp_progress("Setting model parameters")
    if (is.null(mtry_val)) {
        n_predictors <- length(all.vars(formula)[-1])
        if (problem_type == "classification") {
            mtry_val <- floor(sqrt(n_predictors))
        } else {
            mtry_val <- floor(n_predictors / 3)
        }
    }
    
    # Build Random Forest with progress reporting
    rmcp_progress(paste("Building Random Forest with", n_trees, "trees"), 0, 100)
    
    # Custom Random Forest with progress updates
    rf_model <- randomForest(formula, data = data, ntree = n_trees, 
                            mtry = mtry_val, importance = importance)
    
    rmcp_progress("Random Forest construction completed", 100, 100)
    
    # Extract results
    if (problem_type == "classification") {
        confusion_matrix <- rf_model$confusion[, -ncol(rf_model$confusion)]  # Remove class.error column
        oob_error <- rf_model$err.rate[n_trees, "OOB"]
        
        performance <- list(
            oob_error_rate = oob_error,
            confusion_matrix = as.matrix(confusion_matrix),
            class_error = as.list(rf_model$confusion[, "class.error"])
        )
    } else {
        mse <- rf_model$mse[n_trees]
        variance_explained <- (1 - mse / var(data[[response_var]], na.rm = TRUE)) * 100
        
        performance <- list(
            mse = mse,
            rmse = sqrt(mse),
            variance_explained = variance_explained
        )
    }
    
    # Variable importance
    if (importance) {
        var_imp <- importance(rf_model)
        # Convert to proper list format for JSON
        if (is.matrix(var_imp) && !any(is.na(var_imp))) {
            # For classification, use first column or mean if multiple columns
            if (ncol(var_imp) > 1) {
                var_importance <- as.list(var_imp[, 1])
            } else {
                var_importance <- as.list(var_imp[, 1])
            }
        } else if (!is.null(var_imp) && !any(is.na(var_imp))) {
            var_importance <- as.list(var_imp)
        } else {
            # If importance is NA or unavailable, return NULL
            var_importance <- NULL
        }
    } else {
        var_importance <- NULL
    }
    
    # Get OOB error with proper NULL handling
    oob_error_val <- if (problem_type == "classification") {
        oob_error  # Already calculated above
    } else {
        if (!is.null(rf_model$mse) && length(rf_model$mse) >= n_trees) {
            rf_model$mse[n_trees]
        } else {
            NULL
        }
    }
    
    result <- list(
        problem_type = problem_type,
        performance = performance,
        variable_importance = var_importance,
        n_trees = n_trees,
        mtry = rf_model$mtry,
        oob_error = oob_error_val,
        formula = deparse(formula),
        n_obs = nrow(data)
    )
    
    cat(toJSON(result, auto_unbox = FALSE, na = "null"))
    """

    try:
        result = await execute_r_script_async(r_script, params, context)
        await context.info("Random Forest model built successfully")
        return result

    except Exception as e:
        await context.error("Random Forest building failed", error=str(e))
        raise
