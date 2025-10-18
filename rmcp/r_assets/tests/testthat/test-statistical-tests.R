# Tests for statistical tests scripts
library(testthat)
library(jsonlite)

# Test data for statistical tests
test_data1 <- data.frame(
  group = c(rep("A", 10), rep("B", 10)),
  value = c(
    rnorm(10, mean = 5, sd = 1), # Group A
    rnorm(10, mean = 7, sd = 1) # Group B (different mean)
  )
)

test_data2 <- data.frame(
  treatment = c(rep("before", 10), rep("after", 10)),
  score = c(
    c(4, 5, 6, 5, 4, 6, 5, 4, 5, 6), # Before
    c(7, 8, 9, 8, 7, 9, 8, 7, 8, 9) # After (paired)
  )
)

test_that("t_test performs group comparison", {
  input_data <- list(
    data = test_data1,
    formula = "value ~ group",
    alternative = "two.sided"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/statistical_tests/t_test.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("statistic" %in% names(output))
  expect_true("p_value" %in% names(output))
  expect_true("confidence_interval" %in% names(output))
  expect_true("alternative" %in% names(output))

  # P-value should be between 0 and 1
  expect_gte(output$p_value, 0)
  expect_lte(output$p_value, 1)

  # Should match specified alternative hypothesis
  expect_equal(output$alternative, "two.sided")
})

test_that("anova analyzes variance", {
  # Create data with multiple groups
  anova_data <- data.frame(
    group = c(rep("A", 8), rep("B", 8), rep("C", 8)),
    value = c(
      rnorm(8, mean = 5, sd = 1), # Group A
      rnorm(8, mean = 7, sd = 1), # Group B
      rnorm(8, mean = 9, sd = 1) # Group C
    )
  )

  input_data <- list(
    data = anova_data,
    formula = "value ~ group"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/statistical_tests/anova.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("f_statistic" %in% names(output))
  expect_true("p_value" %in% names(output))
  expect_true("degrees_freedom" %in% names(output))

  # F-statistic should be positive
  expect_gte(output$f_statistic, 0)

  # Degrees of freedom should be appropriate for number of groups
  if (is.list(output$degrees_freedom)) {
    expect_equal(length(output$degrees_freedom), 2) # Between and within groups
  }
})

test_that("chi_square_test handles categorical data", {
  # Create contingency table data
  contingency_data <- data.frame(
    factor1 = c(rep("X", 20), rep("Y", 20)),
    factor2 = c(rep(c("1", "2"), each = 10), rep(c("1", "2"), each = 10))
  )

  input_data <- list(
    data = contingency_data,
    formula = "factor1 ~ factor2"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/statistical_tests/chi_square_test.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("statistic" %in% names(output))
  expect_true("p_value" %in% names(output))
  expect_true("degrees_freedom" %in% names(output))

  # Chi-square statistic should be non-negative
  expect_gte(output$statistic, 0)

  # Degrees of freedom should be positive integer
  expect_gt(output$degrees_freedom, 0)
})

test_that("normality_test assesses distribution", {
  # Create clearly normal and non-normal data
  normal_data <- data.frame(values = rnorm(50, mean = 0, sd = 1))

  input_data <- list(
    data = normal_data,
    column = "values",
    test = "shapiro"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/statistical_tests/normality_test.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("test_statistic" %in% names(output))
  expect_true("p_value" %in% names(output))
  expect_true("is_normal" %in% names(output))
  expect_true("test_type" %in% names(output))

  expect_equal(output$test_type, "shapiro")
  expect_true(is.logical(output$is_normal))
})
