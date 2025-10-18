# Tests for regression analysis scripts
library(testthat)
library(jsonlite)

# Test data with clear relationship
test_data <- data.frame(
  x = c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
  y = c(2.1, 3.9, 6.2, 7.8, 10.1, 12.0, 13.9, 16.2, 17.8, 20.1),
  z = c(0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)
)

test_that("linear_model produces valid regression output", {
  input_data <- list(
    data = test_data,
    formula = "y ~ x"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/regression/linear_model.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  # Verify structure
  expect_true(is.list(output))
  expect_true("coefficients" %in% names(output))
  expect_true("r_squared" %in% names(output))
  expect_true("model_summary" %in% names(output))

  # Verify regression results
  expect_true(is.numeric(output$r_squared))
  expect_gte(output$r_squared, 0)
  expect_lte(output$r_squared, 1)

  # Should have intercept and slope
  expect_gte(length(output$coefficients), 2)
})

test_that("correlation_analysis computes correlations", {
  input_data <- list(
    data = test_data,
    method = "pearson"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/regression/correlation_analysis.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("correlation_matrix" %in% names(output))
  expect_true("method" %in% names(output))

  # Correlation matrix should be square
  corr_matrix <- output$correlation_matrix
  expect_equal(nrow(corr_matrix), ncol(corr_matrix))

  # Diagonal should be 1 (correlation with self)
  diag_values <- diag(as.matrix(corr_matrix[, -1])) # Exclude first column if it's row names
  expect_true(all(abs(diag_values - 1) < 1e-10))
})

test_that("logistic_regression handles binary outcomes", {
  # Create binary outcome data
  binary_data <- data.frame(
    x = c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
    outcome = c(0, 0, 0, 0, 1, 1, 1, 1, 1, 1)
  )

  input_data <- list(
    data = binary_data,
    formula = "outcome ~ x"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/regression/logistic_regression.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("coefficients" %in% names(output))
  expect_true("model_summary" %in% names(output))

  # Should have odds ratios for logistic regression
  if ("odds_ratios" %in% names(output)) {
    expect_true(is.numeric(unlist(output$odds_ratios)))
  }
})
