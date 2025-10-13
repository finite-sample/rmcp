# Decision Tree Analysis Script for RMCP
# =======================================
#
# This script builds decision tree models for classification and regression
# with variable importance analysis and performance metrics.


# Load required libraries
library(jsonlite)

# Determine script directory for path resolution
script_dir <- if (exists("testthat_testing") && testthat_testing) {
    # Running under testthat - use relative path from test directory
    file.path("..", "..", "R")
} else {
    # Running normally - use relative path from script location
    file.path("..", "..", "R")
}

# Load RMCP utilities
utils_path <- file.path(script_dir, "utils.R")
if (file.exists(utils_path)) {
    source(utils_path)
} else {
    stop("Cannot find RMCP utilities at: ", utils_path)
}

# Parse command line arguments
args <- if (exists("test_args")) {
    # Use test arguments if provided (for testthat)
    test_args
} else {
    # Parse from command line
    cmd_args <- commandArgs(trailingOnly = TRUE)
    if (length(cmd_args) == 0) {
        stop("No JSON arguments provided")
    }
    
    # Parse JSON input
    tryCatch({
        fromJSON(cmd_args[1])
    }, error = function(e) {
        stop("Failed to parse JSON arguments: ", e$message)
    })
}


# Validate input
args <- validate_json_input(args, required = c("data"))

# Main script logic
library(rpart)

# Prepare data and parameters
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
    tree_complexity = tree_model$cptable[nrow(tree_model$cptable), "CP"],

    # Special non-validated field for formatting
    "_formatting" = list(
        summary = tryCatch({
            # Try to tidy the tree model
            tidy_tree <- broom::tidy(tree_model)
            as.character(knitr::kable(
                tidy_tree, format = "markdown", digits = 4
            ))
        }, error = function(e) {
            # Fallback: create summary table
            tree_summary <- data.frame(
                Model = paste0("Decision Tree (", tree_type, ")"),
                Nodes = nrow(tree_model$frame),
                Complexity = round(tree_model$cptable[nrow(tree_model$cptable), "CP"], 6),
                Observations = nrow(data)
            )
            as.character(knitr::kable(
                tree_summary, format = "markdown", digits = 4
            ))
        }),
        interpretation = paste0("Decision tree (", tree_type, ") with ", nrow(tree_model$frame),
                              " nodes built from ", nrow(data), " observations.")
    )
)
# Output results in standard JSON format
if (exists("result")) {
    cat(safe_json(format_json_output(result)))
} else {
    cat(safe_json(list(error = "No result generated", success = FALSE)))
}
