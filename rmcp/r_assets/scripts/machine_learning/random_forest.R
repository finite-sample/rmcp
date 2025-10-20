# Random Forest Analysis Script for RMCP
# =======================================
#
# This script builds Random Forest ensemble models for classification and regression
# with variable importance analysis and out-of-bag error estimation.

# Load required libraries
library(randomForest)
library(knitr)

# Prepare data and parameters
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
rf_model <- randomForest(formula,
  data = data, ntree = n_trees,
  mtry = mtry_val, importance = importance
)
rmcp_progress("Random Forest construction completed", 100, 100)
# Extract results
if (problem_type == "classification") {
  confusion_matrix <- rf_model$confusion[, -ncol(rf_model$confusion)] # Remove class.error column
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
  oob_error # Already calculated above
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
  n_obs = nrow(data),
  # Special non-validated field for formatting
  "_formatting" = list(
    summary = tryCatch(
      {
        # Create random forest summary table
        rf_summary <- data.frame(
          Model = paste0("Random Forest (", problem_type, ")"),
          Trees = n_trees,
          Mtry = rf_model$mtry,
          OOB_Error = if (is.null(oob_error_val)) NA else round(oob_error_val, 4),
          Observations = nrow(data)
        )
        paste(as.character(knitr::kable(
          rf_summary,
          format = "markdown", digits = 4
        )), collapse = "\n")
      },
      error = function(e) {
        "Random Forest model completed successfully"
      }
    ),
    interpretation = paste0(
      "Random Forest (", problem_type, ") with ", n_trees,
      " trees built from ", nrow(data), " observations."
    )
  )
)
