# Correlation Analysis Script for RMCP
# ====================================
#
# This script calculates pairwise correlations between numeric variables using
# Pearson, Spearman, or Kendall methods. It includes significance tests for
# each correlation and handles missing values appropriately.

# Main script logic
variables <- args$variables
method <- args$method %||% "pearson"
use <- args$use %||% "complete.obs"

# Select variables if specified
if (!is.null(variables)) {
  # Validate variables exist
  missing_vars <- setdiff(variables, names(data))
  if (length(missing_vars) > 0) {
    stop(paste("Variables not found:", paste(missing_vars, collapse = ", ")))
  }
  data <- data[, variables, drop = FALSE]
}

# Select only numeric variables
numeric_vars <- sapply(data, is.numeric)
if (sum(numeric_vars) < 2) {
  stop("Need at least 2 numeric variables for correlation analysis")
}
numeric_data <- data[, numeric_vars, drop = FALSE]

# Compute correlation matrix
cor_matrix <- cor(numeric_data, method = method, use = use)
# Compute significance tests and pairwise n_obs
n <- nrow(numeric_data)
cor_test_results <- list()
# Initialize n_obs matrix structure
n_obs_matrix <- matrix(0, nrow = ncol(numeric_data), ncol = ncol(numeric_data))
rownames(n_obs_matrix) <- names(numeric_data)
colnames(n_obs_matrix) <- names(numeric_data)
# Fill diagonal with total observations
diag(n_obs_matrix) <- n
for (i in 1:(ncol(numeric_data) - 1)) {
  for (j in (i + 1):ncol(numeric_data)) {
    var1 <- names(numeric_data)[i]
    var2 <- names(numeric_data)[j]
    # Filter complete cases for cor.test (cor.test doesn't accept 'use' parameter)
    x <- numeric_data[, i]
    y <- numeric_data[, j]
    complete_cases <- !is.na(x) & !is.na(y)
    n_pairwise <- sum(complete_cases)
    # Store pairwise n_obs in matrix
    n_obs_matrix[i, j] <- n_pairwise
    n_obs_matrix[j, i] <- n_pairwise
    test_result <- cor.test(x[complete_cases], y[complete_cases], method = method)
    cor_test_results[[paste(var1, var2, sep = "_")]] <- list(
      correlation = test_result$estimate,
      p_value = test_result$p.value,
      conf_int_lower = if (!is.null(test_result$conf.int)) test_result$conf.int[1] else NA,
      conf_int_upper = if (!is.null(test_result$conf.int)) test_result$conf.int[2] else NA
    )
  }
}
# Generate formatted summary using our formatting functions (with fallback)
formatted_summary <- format_correlation_matrix(cor_matrix)

# Generate natural language interpretation (with fallback)
# Extract the smallest p-value from significance tests for overall interpretation
min_p <- 1
for (test in cor_test_results) {
  if (!is.na(test$p_value) && test$p_value < min_p) {
    min_p <- test$p_value
  }
}

sig_text <- get_significance(min_p)

interpretation <- paste0("Strongest correlations are ", sig_text, ".")
# Convert correlation matrix to nested list structure
cor_list <- list()
for (var1 in names(numeric_data)) {
  cor_list[[var1]] <- as.list(setNames(cor_matrix[var1, ], names(numeric_data)))
}
# Convert n_obs matrix to nested list structure
n_obs_list <- list()
for (var1 in names(numeric_data)) {
  n_obs_list[[var1]] <- as.list(setNames(n_obs_matrix[var1, ], names(numeric_data)))
}
result <- list(
  # Schema-compliant fields only (strict validation)
  correlation_matrix = cor_list,
  significance_tests = cor_test_results,
  method = method,
  n_obs = n_obs_list,
  variables = names(numeric_data),
  # Special non-validated field for formatting (will be extracted before validation)
  "_formatting" = list(
    summary = formatted_summary,
    interpretation = interpretation
  )
)
