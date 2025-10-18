# Tests for utility functions
library(testthat)
library(jsonlite)

# Source the utility functions
source("../../R/utils.R")

test_that("rmcp_progress outputs correctly", {
  # Capture stderr output
  output <- capture.output(
    rmcp_progress("Testing progress", current = 50, total = 100),
    type = "message"
  )

  expect_length(output, 1)
  expect_true(grepl("RMCP_PROGRESS:", output))

  # Parse the JSON part
  json_part <- sub("RMCP_PROGRESS: ", "", output)
  progress_data <- fromJSON(json_part)

  expect_equal(progress_data$type, "progress")
  expect_equal(progress_data$message, "Testing progress")
  expect_equal(progress_data$current, 50)
  expect_equal(progress_data$total, 100)
  expect_equal(progress_data$percentage, 50)
})

test_that("validate_json_input validates required parameters", {
  valid_params <- list(
    data = data.frame(x = 1:5, y = 6:10),
    formula = "y ~ x"
  )

  # Should pass validation
  result <- validate_json_input(valid_params,
    required = c("data", "formula")
  )
  expect_equal(result, valid_params)

  # Should fail with missing required parameter
  expect_error(
    validate_json_input(list(data = valid_params$data),
      required = c("data", "formula")
    ),
    "Missing required parameters: formula"
  )
})

test_that("validate_json_input handles data conversion", {
  # Test list to data frame conversion
  list_data <- list(x = c(1, 2, 3), y = c(4, 5, 6))
  params <- list(data = list_data)

  result <- validate_json_input(params, required = "data")
  expect_true(is.data.frame(result$data))
  expect_equal(ncol(result$data), 2)
  expect_equal(nrow(result$data), 3)
})

test_that("validate_json_input validates formulas", {
  params <- list(
    data = data.frame(x = 1:5, y = 6:10),
    formula = "y ~ x"
  )

  # Valid formula should pass
  result <- validate_json_input(params, required = c("data", "formula"))
  expect_equal(result$formula, "y ~ x")

  # Invalid formula should fail
  params$formula <- "y ~~ x invalid"
  expect_error(
    validate_json_input(params, required = c("data", "formula")),
    "Invalid formula syntax"
  )
})

test_that("format_json_output handles special values", {
  test_data <- list(
    normal_value = 1.23456789,
    infinite_value = Inf,
    negative_infinite = -Inf,
    na_value = NA,
    nan_value = NaN,
    very_large = 1e15,
    very_small = 1e-15
  )

  result <- format_json_output(test_data)

  # Normal value should be rounded
  expect_equal(result$normal_value, round(1.23456789, 10))

  # Special values should be converted to strings or null
  expect_equal(result$infinite_value, "Inf")
  expect_equal(result$negative_infinite, "-Inf")
  expect_null(result$na_value)
  expect_null(result$nan_value)

  # Large/small values should use scientific notation
  expect_true(is.character(result$very_large))
  expect_true(grepl("e", result$very_large))
})

test_that("format_json_output adds formatting metadata", {
  result <- format_json_output(
    list(value = 42),
    summary = "Test summary",
    interpretation = "Test interpretation"
  )

  expect_true("_formatting" %in% names(result))
  expect_equal(result$`_formatting`$summary, "Test summary")
  expect_equal(result$`_formatting`$interpretation, "Test interpretation")
})

test_that("null-coalescing operator works correctly", {
  # Test with NULL and non-NULL values
  expect_equal(NULL %||% "default", "default")
  expect_equal("value" %||% "default", "value")
  expect_equal(0 %||% "default", 0)
  expect_equal(FALSE %||% "default", FALSE)
})

test_that("check_packages detects available packages", {
  # Test with base R packages (should always be available)
  result <- check_packages(c("base", "stats"))
  expect_true(all(result))
  expect_equal(length(result), 2)

  # Test with non-existent package
  result <- check_packages("nonexistent_package_xyz123")
  expect_false(result)
})

test_that("check_packages stops on missing packages when requested", {
  expect_error(
    check_packages("nonexistent_package_xyz123", stop_on_missing = TRUE),
    "Missing required R packages"
  )
})

test_that("safe_json handles factors and special values", {
  test_data <- list(
    factor_col = factor(c("A", "B", "C")),
    numeric_col = c(1, 2, Inf, -Inf, NA),
    logical_col = c(TRUE, FALSE, NA)
  )

  json_str <- safe_json(test_data)

  # Should be valid JSON
  expect_true(is.character(json_str))
  expect_true(jsonlite::validate(json_str))

  # Parse back and check factor conversion
  parsed <- fromJSON(json_str)
  expect_true(is.character(parsed$factor_col))
  expect_equal(parsed$factor_col, c("A", "B", "C"))
})
