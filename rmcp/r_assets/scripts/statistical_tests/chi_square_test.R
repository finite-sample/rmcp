# Chi-Square Test Analysis Script for RMCP
# ========================================
#
# This script performs chi-square tests for independence and goodness of fit.
# It supports testing relationships between categorical variables and comparing
# observed frequencies to expected distributions.

# Prepare data and parameters
test_type <- args$test_type %||% "independence"
x_var <- args$x
y_var <- args$y
expected_probs <- args$expected

# Load required libraries
if (test_type == "independence") {
  if (is.null(x_var) || is.null(y_var)) {
    stop("Both x and y variables required for independence test")
  }

  # Create contingency table
  cont_table <- table(data[[x_var]], data[[y_var]])
  test_result <- chisq.test(cont_table)

  result <- list(
    test_type = "Chi-square test of independence",
    contingency_table = as.matrix(cont_table),
    statistic = as.numeric(test_result$statistic),
    df = test_result$parameter,
    p_value = test_result$p.value,
    expected_frequencies = as.matrix(test_result$expected),
    residuals = as.matrix(test_result$residuals),
    x_variable = x_var,
    y_variable = y_var,
    cramers_v = sqrt(test_result$statistic / (sum(cont_table) * (min(dim(cont_table)) - 1))),
    # Special non-validated field for formatting
    "_formatting" = list(
      summary = format_result_table(test_result, "Chi-Square Test"),
      interpretation = interpret_result(test_result, "Chi-square test")
    )
  )
} else {
  # Goodness of fit test
  if (is.null(x_var)) {
    stop("x variable required for goodness of fit test")
  }
  observed <- table(data[[x_var]])
  if (!is.null(expected)) {
    # Validate expected probabilities
    if (length(expected) != length(observed)) {
      stop(paste(
        "Expected probabilities length (", length(expected),
        ") must match number of categories (", length(observed), ")"
      ))
    }
    if (any(expected < 0)) {
      stop("Expected probabilities must be non-negative")
    }
    if (sum(expected) == 0) {
      stop("Expected probabilities cannot all be zero")
    }
    # Normalize to probabilities (sum to 1)
    p <- expected / sum(expected)
    names(p) <- names(observed)
    test_result <- chisq.test(observed, p = p)
    # Warn about low expected counts
    expected_counts <- test_result$expected
    low_expected <- sum(expected_counts < 5)
    if (low_expected > 0) {
      warning(paste(low_expected, "cell(s) have expected counts < 5. Results may be unreliable."))
    }
  } else {
    test_result <- chisq.test(observed)
  }
  result <- list(
    test_type = "Chi-square goodness of fit test",
    observed_frequencies = as.numeric(observed),
    expected_frequencies = as.numeric(test_result$expected),
    statistic = as.numeric(test_result$statistic),
    df = test_result$parameter,
    p_value = test_result$p.value,
    residuals = as.numeric(test_result$residuals),
    categories = names(observed),
    # Special non-validated field for formatting
    "_formatting" = list(
      summary = format_result_table(test_result, "Chi-Square Goodness of Fit"),
      interpretation = interpret_result(test_result, "Chi-square test")
    )
  )
}
