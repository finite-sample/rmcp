# Tests for machine learning scripts
library(testthat)
library(jsonlite)

# Test data for clustering and classification
ml_data <- data.frame(
  x1 = c(1, 2, 3, 8, 9, 10, 1.5, 2.5, 3.5, 8.5, 9.5, 10.5),
  x2 = c(1, 2, 3, 8, 9, 10, 2, 3, 4, 9, 10, 11),
  class = c(rep("A", 6), rep("B", 6))
)

test_that("kmeans_clustering produces valid clusters", {
  input_data <- list(
    data = ml_data[, 1:2], # Only numeric columns
    k = 2,
    algorithm = "Hartigan-Wong"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/machine_learning/kmeans_clustering.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("clusters" %in% names(output))
  expect_true("centers" %in% names(output))
  expect_true("within_ss" %in% names(output))

  # Should have cluster assignment for each observation
  expect_equal(length(output$clusters), nrow(ml_data))

  # Should have k centers
  expect_equal(nrow(output$centers), 2)

  # Cluster assignments should be integers from 1 to k
  expect_true(all(output$clusters %in% 1:2))
})

test_that("decision_tree builds classification tree", {
  input_data <- list(
    data = ml_data,
    formula = "class ~ x1 + x2"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/machine_learning/decision_tree.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("tree_summary" %in% names(output))
  expect_true("variable_importance" %in% names(output))

  # Should have predictions for training data
  if ("predictions" %in% names(output)) {
    expect_equal(length(output$predictions), nrow(ml_data))
  }
})

test_that("random_forest handles classification", {
  input_data <- list(
    data = ml_data,
    formula = "class ~ x1 + x2",
    ntree = 100,
    mtry = 1
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/machine_learning/random_forest.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("model_summary" %in% names(output))
  expect_true("variable_importance" %in% names(output))

  # Should have error rate information
  if ("oob_error" %in% names(output)) {
    expect_true(is.numeric(output$oob_error))
    expect_gte(output$oob_error, 0)
    expect_lte(output$oob_error, 1)
  }

  # Variable importance should include all predictors
  var_imp <- output$variable_importance
  expect_true(is.data.frame(var_imp) || is.list(var_imp))
})
