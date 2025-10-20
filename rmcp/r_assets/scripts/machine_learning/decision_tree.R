# Decision Tree Analysis Script for RMCP
# =======================================
#
# This script builds decision tree models for classification and regression
# with variable importance analysis and performance metrics.

# Load required libraries
library(rpart)
library(knitr)
library(broom)

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
tree_model <- rpart(formula,
  data = data, method = method,
  control = rpart.control(minsplit = min_split, maxdepth = max_depth)
)

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
    confusion_matrix = lapply(seq_len(nrow(confusion_matrix)), function(i) as.numeric(confusion_matrix[i, ]))
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
if (is.null(var_importance) || length(var_importance) == 0) {
  # Create empty named list to ensure it's an object in JSON
  var_importance <- setNames(list(), character(0))
} else {
  var_importance <- as.list(var_importance)
}
result <- list(
  tree_type = tree_type,
  performance = performance,
  variable_importance = var_importance,
  predictions = as.numeric(predictions),
  n_nodes = nrow(tree_model$frame),
  n_obs = nrow(data),
  formula = deparse(formula),
  tree_complexity = tree_model$cptable[nrow(tree_model$cptable), "CP"],
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Try to tidy the tree model
        tidy_tree <- broom::tidy(tree_model)
        paste(as.character(knitr::kable(
          tidy_tree,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        # Fallback: create summary table
        tree_summary <- data.frame(
          Model = paste0("Decision Tree (", tree_type, ")"),
          Nodes = nrow(tree_model$frame),
          Complexity = round(tree_model$cptable[nrow(tree_model$cptable), "CP"], 6),
          Observations = nrow(data)
        )
        paste(as.character(knitr::kable(
          tree_summary,
          format = "markdown", digits = 4
        )), collapse = "\n")
      }
    ),
    interpretation = paste0(
      "Decision tree (", tree_type, ") with ", nrow(tree_model$frame),
      " nodes built from ", nrow(data), " observations."
    )
  )
)
