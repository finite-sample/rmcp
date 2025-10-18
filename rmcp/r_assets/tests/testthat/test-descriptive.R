# Tests for descriptive statistics scripts
library(testthat)
library(jsonlite)

# Test data
test_data <- data.frame(
  x = c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
  y = c(2, 4, 6, 8, 10, 12, 14, 16, 18, 20),
  category = c("A", "A", "B", "B", "A", "B", "A", "B", "A", "B")
)

test_that("summary_stats produces valid output", {
  # Create test input
  input_data <- list(data = test_data)
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  # Run script
  result <- system2("Rscript",
    args = c("../../scripts/descriptive/summary_stats.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  # Parse result
  output <- fromJSON(result[length(result)])

  # Verify structure
  expect_true(is.list(output))
  expect_true("variables" %in% names(output))
  expect_true("summary_stats" %in% names(output))

  # Verify statistics
  expect_equal(length(output$variables), 3) # x, y, category
  expect_true(all(c("mean", "median", "sd") %in% names(output$summary_stats)))
})

test_that("frequency_table handles categorical data", {
  input_data <- list(
    data = test_data,
    column = "category"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/descriptive/frequency_table.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("frequency_table" %in% names(output))
  expect_true("summary" %in% names(output))

  # Check frequency counts
  freq_table <- output$frequency_table
  expect_equal(nrow(freq_table), 2) # A and B categories
  expect_true(all(c("value", "count", "percentage") %in% names(freq_table)))
})

test_that("outlier_detection identifies outliers correctly", {
  # Create data with obvious outliers
  outlier_data <- data.frame(
    values = c(1, 2, 3, 4, 5, 100, 200) # 100, 200 are outliers
  )

  input_data <- list(
    data = outlier_data,
    column = "values",
    method = "iqr"
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/descriptive/outlier_detection.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("outliers" %in% names(output))
  expect_true("outlier_count" %in% names(output))
  expect_true("method" %in% names(output))

  # Should detect the extreme values as outliers
  expect_gt(output$outlier_count, 0)
  expect_equal(output$method, "iqr")
})
