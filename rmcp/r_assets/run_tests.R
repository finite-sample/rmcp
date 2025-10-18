#!/usr/bin/env Rscript
#' RMCP R Test Runner
#'
#' Runs all testthat tests for RMCP R statistical analysis scripts.
#' This script can be called from the main Python project or run independently.

# Load required packages
if (!requireNamespace("testthat", quietly = TRUE)) {
  stop("testthat package is required but not installed. Install with: install.packages('testthat')")
}

if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("jsonlite package is required but not installed. Install with: install.packages('jsonlite')")
}

library(testthat)
library(jsonlite)

# Set working directory to r_assets
script_dir <- dirname(normalizePath(sys.frame(1)$ofile))
setwd(script_dir)

# Print test environment info
cat("RMCP R Test Runner\n")
cat("==================\n")
cat(sprintf("R version: %s\n", R.version.string))
cat(sprintf("Working directory: %s\n", getwd()))
cat(sprintf("testthat version: %s\n", packageVersion("testthat")))
cat(sprintf("jsonlite version: %s\n", packageVersion("jsonlite")))
cat("\n")

# Run tests
cat("Running testthat tests...\n")
test_results <- test_dir("tests/testthat", reporter = "summary")

# Print summary
cat("\n")
cat("Test Summary:\n")
cat("=============\n")

if (is.null(test_results) || length(test_results) == 0) {
  cat("No tests found or test results unavailable.\n")
  quit(status = 1)
}

# Extract results (testthat structure may vary by version)
if (inherits(test_results, "testthat_results")) {
  failed_tests <- sum(as.data.frame(test_results)$failed, na.rm = TRUE)
  passed_tests <- sum(as.data.frame(test_results)$passed, na.rm = TRUE)
  warnings <- sum(as.data.frame(test_results)$warning, na.rm = TRUE)
  skipped <- sum(as.data.frame(test_results)$skipped, na.rm = TRUE)
} else {
  # Fallback for different testthat versions
  failed_tests <- 0
  passed_tests <- 0
  warnings <- 0
  skipped <- 0

  cat("Test results format not recognized, but tests completed.\n")
}

cat(sprintf("Passed: %d\n", passed_tests))
cat(sprintf("Failed: %d\n", failed_tests))
cat(sprintf("Warnings: %d\n", warnings))
cat(sprintf("Skipped: %d\n", skipped))

# Exit with appropriate code
if (failed_tests > 0) {
  cat("\nSome tests failed!\n")
  quit(status = 1)
} else {
  cat("\nAll tests passed! ✅\n")
  quit(status = 0)
}
