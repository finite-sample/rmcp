# Tests for file operations scripts
library(testthat)
library(jsonlite)

# Create temporary test files
temp_dir <- tempdir()
test_csv <- file.path(temp_dir, "test_data.csv")
test_excel <- file.path(temp_dir, "test_data.xlsx")
test_json <- file.path(temp_dir, "test_data.json")

# Sample data
sample_data <- data.frame(
  id = 1:5,
  name = c("Alice", "Bob", "Charlie", "Diana", "Eve"),
  score = c(85, 92, 78, 96, 89),
  passed = c(TRUE, TRUE, FALSE, TRUE, TRUE)
)

# Setup: Create test files
write.csv(sample_data, test_csv, row.names = FALSE)
write(toJSON(sample_data), test_json)

test_that("read_csv loads CSV files correctly", {
  input_data <- list(file_path = test_csv)
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/fileops/read_csv.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("data" %in% names(output))
  expect_true("metadata" %in% names(output))

  # Should have same number of rows and columns
  expect_equal(output$metadata$rows, nrow(sample_data))
  expect_equal(output$metadata$columns, ncol(sample_data))

  # Data should be a data frame structure
  expect_true(is.data.frame(output$data) || is.list(output$data))
})

test_that("read_json loads JSON files correctly", {
  input_data <- list(file_path = test_json)
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/fileops/read_json.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("data" %in% names(output))
  expect_true("metadata" %in% names(output))

  # Should load the same structure
  expect_equal(output$metadata$rows, nrow(sample_data))
})

test_that("write_csv creates CSV files", {
  output_path <- file.path(temp_dir, "output_test.csv")

  input_data <- list(
    data = sample_data,
    file_path = output_path
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/fileops/write_csv.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("success" %in% names(output))
  expect_true("file_path" %in% names(output))

  # File should exist
  expect_true(file.exists(output_path))

  # Clean up
  if (file.exists(output_path)) {
    unlink(output_path)
  }
})

test_that("data_info provides file metadata", {
  input_data <- list(file_path = test_csv)
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/fileops/data_info.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("file_info" %in% names(output))
  expect_true("data_summary" %in% names(output))

  file_info <- output$file_info
  expect_true("size_bytes" %in% names(file_info))
  expect_true("file_type" %in% names(file_info))

  data_summary <- output$data_summary
  expect_true("rows" %in% names(data_summary))
  expect_true("columns" %in% names(data_summary))
})

test_that("filter_data applies conditions correctly", {
  input_data <- list(
    data = sample_data,
    conditions = list(
      list(column = "score", operator = ">", value = 85)
    )
  )
  input_json <- toJSON(input_data, auto_unbox = TRUE)

  result <- system2("Rscript",
    args = c("../../scripts/fileops/filter_data.R", input_json),
    stdout = TRUE, stderr = TRUE
  )

  output <- fromJSON(result[length(result)])

  expect_true(is.list(output))
  expect_true("filtered_data" %in% names(output))
  expect_true("filter_summary" %in% names(output))

  # Should have fewer rows than original (scores > 85)
  expect_lt(output$filter_summary$rows_after, nrow(sample_data))
  expect_gt(output$filter_summary$rows_after, 0)
})

# Cleanup
if (file.exists(test_csv)) unlink(test_csv)
if (file.exists(test_json)) unlink(test_json)
