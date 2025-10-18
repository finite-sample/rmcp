#!/usr/bin/env Rscript
#' RMCP R Linting Script
#'
#' Runs lintr on RMCP R statistical analysis scripts and utility functions.
#' This script can be called from the main Python project or run independently.

# Check if lintr is available
if (!requireNamespace("lintr", quietly = TRUE)) {
  cat("lintr package is required but not installed.\n")
  cat("Installing lintr...\n")
  install.packages("lintr", repos = "https://cran.r-project.org")
}

library(lintr)

# Set working directory to r_assets
script_dir <- dirname(normalizePath(sys.frame(1)$ofile))
setwd(script_dir)

cat("RMCP R Linting Tool\n")
cat("===================\n")
cat(sprintf("Working directory: %s\n", getwd()))
cat(sprintf("lintr version: %s\n", packageVersion("lintr")))
cat("\n")

# Function to lint specific files or directories
lint_files <- function(paths, title) {
  cat(sprintf("Linting %s...\n", title))
  cat(sprintf("Files: %s\n", paste(paths, collapse = ", ")))

  all_results <- list()

  for (path in paths) {
    if (file.exists(path)) {
      if (file.info(path)$isdir) {
        # Lint all R files in directory
        r_files <- list.files(path, pattern = "\\.R$", recursive = TRUE, full.names = TRUE)
        for (r_file in r_files) {
          tryCatch(
            {
              results <- lint(r_file)
              if (length(results) > 0) {
                all_results[[r_file]] <- results
              }
            },
            error = function(e) {
              cat(sprintf("Error linting %s: %s\n", r_file, e$message))
            }
          )
        }
      } else {
        # Lint single file
        tryCatch(
          {
            results <- lint(path)
            if (length(results) > 0) {
              all_results[[path]] <- results
            }
          },
          error = function(e) {
            cat(sprintf("Error linting %s: %s\n", path, e$message))
          }
        )
      }
    } else {
      cat(sprintf("⚠️ Path not found: %s\n", path))
    }
  }

  return(all_results)
}

# Function to print lint results
print_lint_results <- function(results, title) {
  if (length(results) == 0) {
    cat(sprintf("✅ %s: No linting issues found\n", title))
    return(TRUE)
  }

  cat(sprintf("❌ %s: %d files with linting issues\n", title, length(results)))

  total_issues <- 0
  for (file_path in names(results)) {
    file_results <- results[[file_path]]
    cat(sprintf("\n📁 %s (%d issues):\n", file_path, length(file_results)))

    for (issue in file_results) {
      cat(sprintf(
        "  Line %d: %s [%s]\n",
        issue$line_number %||% "?",
        issue$message %||% "Unknown issue",
        issue$linter %||% "unknown"
      ))
      total_issues <- total_issues + 1
    }
  }

  cat(sprintf("\nTotal issues: %d\n", total_issues))
  return(FALSE)
}

# Lint utility functions
cat("1. Linting utility functions...\n")
utils_results <- lint_files(c("R/utils.R"), "utility functions")
utils_clean <- print_lint_results(utils_results, "Utility Functions")

# Lint test files
cat("\n2. Linting test files...\n")
test_results <- lint_files(c("tests/testthat"), "test files")
tests_clean <- print_lint_results(test_results, "Test Files")

# Lint statistical scripts (sample)
cat("\n3. Linting statistical scripts (sample)...\n")
script_paths <- c(
  "scripts/descriptive/summary_stats.R",
  "scripts/regression/linear_model.R",
  "scripts/timeseries/arima_model.R",
  "scripts/machine_learning/kmeans_clustering.R"
)
scripts_results <- lint_files(script_paths, "statistical scripts")
scripts_clean <- print_lint_results(scripts_results, "Statistical Scripts")

# Overall summary
cat("\n" %rep% 50)
cat("LINTING SUMMARY\n")
cat("===============\n")

if (utils_clean && tests_clean && scripts_clean) {
  cat("🎉 All linting checks passed!\n")
  cat("✅ Code follows R style guidelines\n")
  quit(status = 0)
} else {
  cat("⚠️ Linting issues found\n")
  cat("Please review and fix the issues above\n")

  # Provide helpful guidance
  cat("\nCommon fixes:\n")
  cat("- Use snake_case for function and variable names\n")
  cat("- Keep lines under 100 characters\n")
  cat("- Use proper spacing around operators\n")
  cat("- Remove trailing whitespace\n")
  cat("- Use <- for assignment instead of =\n")

  quit(status = 1)
}

# Helper operator for string repetition
`%rep%` <- function(str, n) paste(rep(str, n), collapse = "")

# Helper for null-coalescing (if not already defined)
if (!exists("%||%")) {
  `%||%` <- function(a, b) if (is.null(a)) b else a
}
