#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
if (length(file_arg) != 1) {
  stop("Unable to determine the test runner path")
}

script_path <- sub("^--file=", "", file_arg)
script_dir <- dirname(normalizePath(script_path))

if (!requireNamespace("testthat", quietly = TRUE)) {
  stop("testthat is required")
}

source(file.path(script_dir, "R", "utils.R"))
testthat::test_dir(
  file.path(script_dir, "tests", "testthat"),
  reporter = "summary",
  stop_on_failure = TRUE
)
