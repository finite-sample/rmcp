"""
Machine learning tools for RMCP.

Clustering, classification trees, and ML capabilities.
"""

from typing import Dict, Any
from ..registries.tools import tool
from ..core.schemas import table_schema, formula_schema
from ..r_integration import execute_r_script


@tool(
    name="kmeans_clustering",
    input_schema={
        "type": "object",
        "properties": {
            "data": table_schema(),
            "variables": {"type": "array", "items": {"type": "string"}},
            "k": {"type": "integer", "minimum": 2, "maximum": 20},
            "max_iter": {"type": "integer", "minimum": 1, "default": 100},
            "nstart": {"type": "integer", "minimum": 1, "default": 25}
        },
        "required": ["data", "variables", "k"]
    },
    description="K-means clustering analysis with cluster validation"
)
async def kmeans_clustering(context, params):
    """Perform K-means clustering."""
    
    await context.info("Performing K-means clustering")
    
    r_script = '''
    data <- as.data.frame(args$data)
    variables <- args$variables
    k <- args$k
    max_iter <- args$max_iter %||% 100
    nstart <- args$nstart %||% 25
    
    # Select and prepare data
    cluster_data <- data[, variables, drop = FALSE]
    cluster_data <- na.omit(cluster_data)
    
    # Scale variables for clustering
    scaled_data <- scale(cluster_data)
    
    # Perform k-means
    set.seed(123)  # For reproducibility
    kmeans_result <- kmeans(scaled_data, centers = k, iter.max = max_iter, nstart = nstart)
    
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
    
    # Silhouette analysis (if package available)
    silhouette_score <- NA
    if (require(cluster, quietly = TRUE)) {
        library(cluster)
        sil <- silhouette(cluster_assignments, dist(scaled_data))
        silhouette_score <- mean(sil[, 3])
    }
    
    result <- list(
        cluster_assignments = cluster_assignments,
        cluster_centers = as.data.frame(cluster_centers),
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
    '''
    
    try:
        result = execute_r_script(r_script, params)
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
            "type": {"type": "string", "enum": ["classification", "regression"], "default": "classification"},
            "min_split": {"type": "integer", "minimum": 1, "default": 20},
            "max_depth": {"type": "integer", "minimum": 1, "default": 30}
        },
        "required": ["data", "formula"]
    },
    description="Decision tree classification and regression"
)
async def decision_tree(context, params):
    """Build decision tree model."""
    
    await context.info("Building decision tree")
    
    r_script = '''
    if (!require(rpart)) install.packages("rpart", quietly = TRUE)
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
    '''
    
    try:
        result = execute_r_script(r_script, params)
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
            "n_trees": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 500},
            "mtry": {"type": "integer", "minimum": 1},
            "importance": {"type": "boolean", "default": True}
        },
        "required": ["data", "formula"]
    },
    description="Random Forest ensemble model for classification and regression"
)
async def random_forest(context, params):
    """Build Random Forest model."""
    
    await context.info("Building Random Forest model")
    
    r_script = '''
    if (!require(randomForest)) install.packages("randomForest", quietly = TRUE)
    library(randomForest)
    
    data <- as.data.frame(args$data)
    formula <- as.formula(args$formula)
    n_trees <- args$n_trees %||% 500
    mtry_val <- args$mtry
    importance <- args$importance %||% TRUE
    
    # Determine problem type
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
    if (is.null(mtry_val)) {
        n_predictors <- length(all.vars(formula)[-1])
        if (problem_type == "classification") {
            mtry_val <- floor(sqrt(n_predictors))
        } else {
            mtry_val <- floor(n_predictors / 3)
        }
    }
    
    # Build Random Forest
    rf_model <- randomForest(formula, data = data, ntree = n_trees, 
                            mtry = mtry_val, importance = importance)
    
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
        var_importance <- as.data.frame(var_imp)
    } else {
        var_importance <- NULL
    }
    
    result <- list(
        problem_type = problem_type,
        performance = performance,
        variable_importance = var_importance,
        n_trees = n_trees,
        mtry = rf_model$mtry,
        oob_error = rf_model$err.rate[n_trees, 1],
        formula = deparse(formula),
        n_obs = nrow(data)
    )
    '''
    
    try:
        result = execute_r_script(r_script, params)
        await context.info("Random Forest model built successfully")
        return result
        
    except Exception as e:
        await context.error("Random Forest building failed", error=str(e))
        raise