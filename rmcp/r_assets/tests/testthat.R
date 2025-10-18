# Test runner configuration for RMCP R scripts
# This file is used by R CMD check and testthat::test_package()

library(testthat)
library(jsonlite)

# Set up test environment
Sys.setenv("RMCP_TEST_MODE" = "true")

# Configure testthat options
options(testthat.progress.max_fails = 10)

# Source utility functions
source(file.path("..", "R", "utils.R"))

# Run all tests in the testthat directory
cat("Running RMCP R statistical analysis tests...\n")
test_check("rmcp.stats")
