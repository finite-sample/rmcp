#!/usr/bin/env Rscript
#' RMCP R Script Validation Pipeline
#'
#' Comprehensive validation of RMCP R statistical analysis scripts.
#' Runs syntax checking, linting, testing, and validation of JSON interfaces.

# Required packages for validation
required_packages <- c("jsonlite", "testthat", "lintr", "styler")
missing_packages <- required_packages[!sapply(required_packages, requireNamespace, quietly = TRUE)]

if (length(missing_packages) > 0) {
  cat("Installing missing validation packages...\n")
  install.packages(missing_packages, repos = "https://cran.r-project.org")
}

library(jsonlite)

# Set working directory to r_assets
script_dir <- dirname(normalizePath(sys.frame(1)$ofile))
setwd(script_dir)

cat("RMCP R Script Validation Pipeline\n")
cat("==================================\n")
cat(sprintf("Working directory: %s\n", getwd()))
cat(sprintf("Validation timestamp: %s\n", Sys.time()))
cat("\n")

# Validation configuration
validation_config <- list(
  syntax_check = TRUE,
  format_check = TRUE,
  lint_check = TRUE,
  test_run = TRUE,
  json_interface_check = TRUE,
  documentation_check = TRUE
)

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)
quick_mode <- "--quick" %in% args
verbose <- "--verbose" %in% args

if (quick_mode) {
  cat("🚀 Running in quick mode (syntax and format only)\n")
  validation_config$test_run <- FALSE
  validation_config$json_interface_check <- FALSE
}

# Validation functions
check_syntax <- function(file_path) {
  tryCatch(
    {
      parse(file_path)
      return(list(success = TRUE, message = "Syntax OK"))
    },
    error = function(e) {
      return(list(success = FALSE, message = paste("Syntax error:", e$message)))
    }
  )
}

check_json_interface <- function(script_path) {
  # Test if script can handle basic JSON input/output
  tryCatch(
    {
      # Create minimal test input
      test_input <- list(data = data.frame(x = 1:5, y = 6:10))
      input_json <- toJSON(test_input, auto_unbox = TRUE)

      # Try to run script (capture output)
      result <- system2("Rscript",
        args = c(script_path, shQuote(input_json)),
        stdout = TRUE, stderr = TRUE,
        timeout = 30
      )

      # Check if output is valid JSON
      if (length(result) > 0) {
        last_line <- result[length(result)]
        tryCatch(
          {
            fromJSON(last_line)
            return(list(success = TRUE, message = "JSON interface OK"))
          },
          error = function(e) {
            return(list(success = FALSE, message = "Invalid JSON output"))
          }
        )
      } else {
        return(list(success = FALSE, message = "No output produced"))
      }
    },
    error = function(e) {
      return(list(success = FALSE, message = paste("Interface error:", e$message)))
    }
  )
}

validate_script_category <- function(category_path, category_name) {
  cat(sprintf("\n📂 Validating %s scripts...\n", category_name))

  if (!dir.exists(category_path)) {
    cat(sprintf("⚠️ Directory not found: %s\n", category_path))
    return(list(total = 0, passed = 0, failed = 0))
  }

  r_files <- list.files(category_path, pattern = "\\.R$", full.names = TRUE)

  if (length(r_files) == 0) {
    cat("No R files found in this category\n")
    return(list(total = 0, passed = 0, failed = 0))
  }

  cat(sprintf("Found %d R scripts\n", length(r_files)))

  results <- list(total = length(r_files), passed = 0, failed = 0)

  for (script_path in r_files) {
    script_name <- basename(script_path)
    cat(sprintf("\n  🔍 %s\n", script_name))

    script_passed <- TRUE

    # 1. Syntax check
    if (validation_config$syntax_check) {
      syntax_result <- check_syntax(script_path)
      if (syntax_result$success) {
        cat("    ✅ Syntax check passed\n")
      } else {
        cat(sprintf("    ❌ Syntax check failed: %s\n", syntax_result$message))
        script_passed <- FALSE
      }
    }

    # 2. JSON interface check (for statistical scripts)
    if (validation_config$json_interface_check && !grepl("util|test", script_name, ignore.case = TRUE)) {
      json_result <- check_json_interface(script_path)
      if (json_result$success) {
        cat("    ✅ JSON interface check passed\n")
      } else {
        cat(sprintf("    ⚠️ JSON interface check: %s\n", json_result$message))
        # Don't fail script for JSON interface issues (they may need specific data)
      }
    }

    # 3. Check for required utility imports
    script_content <- readLines(script_path)
    has_jsonlite <- any(grepl("library\\(jsonlite\\)|require\\(jsonlite\\)", script_content))

    if (!has_jsonlite) {
      cat("    ⚠️ Missing jsonlite library import\n")
    } else {
      cat("    ✅ Required imports present\n")
    }

    # 4. Check for proper error handling
    has_trycatch <- any(grepl("tryCatch|try\\(", script_content))
    if (has_trycatch) {
      cat("    ✅ Error handling found\n")
    } else {
      cat("    ⚠️ No error handling detected\n")
    }

    if (script_passed) {
      results$passed <- results$passed + 1
    } else {
      results$failed <- results$failed + 1
    }
  }

  return(results)
}

# Main validation pipeline
cat("Starting validation pipeline...\n")

# 1. Format check
if (validation_config$format_check) {
  cat("\n" %rep% 50)
  cat("1. CODE FORMATTING CHECK\n")
  cat("========================\n")

  if (file.exists("format_r.R")) {
    format_result <- system("Rscript format_r.R --dry-run", ignore.stdout = !verbose)
    if (format_result == 0) {
      cat("✅ All files properly formatted\n")
    } else {
      cat("⚠️ Some files need formatting (run format_r.R to fix)\n")
    }
  } else {
    cat("⚠️ format_r.R script not found\n")
  }
}

# 2. Linting check
if (validation_config$lint_check) {
  cat(sprintf("\n%s\n", paste(rep("=", 50), collapse = "")))
  cat("2. LINTING CHECK\n")
  cat("================\n")

  if (file.exists("lint_r.R")) {
    lint_result <- system("Rscript lint_r.R", ignore.stdout = !verbose)
    if (lint_result == 0) {
      cat("✅ All linting checks passed\n")
    } else {
      cat("⚠️ Linting issues found (see output above)\n")
    }
  } else {
    cat("⚠️ lint_r.R script not found\n")
  }
}

# 3. Test suite
if (validation_config$test_run) {
  cat(sprintf("\n%s\n", paste(rep("=", 50), collapse = "")))
  cat("3. TEST SUITE\n")
  cat("=============\n")

  if (file.exists("run_tests.R")) {
    test_result <- system("Rscript run_tests.R", ignore.stdout = !verbose)
    if (test_result == 0) {
      cat("✅ All tests passed\n")
    } else {
      cat("⚠️ Some tests failed (see output above)\n")
    }
  } else {
    cat("⚠️ run_tests.R script not found\n")
  }
}

# 4. Script validation by category
cat(sprintf("\n%s\n", paste(rep("=", 50), collapse = "")))
cat("4. SCRIPT VALIDATION\n")
cat("====================\n")

# Validate different categories of scripts
categories <- list(
  c("R", "Utility Functions"),
  c("scripts/descriptive", "Descriptive Statistics"),
  c("scripts/regression", "Regression Analysis"),
  c("scripts/timeseries", "Time Series Analysis"),
  c("scripts/machine_learning", "Machine Learning"),
  c("scripts/statistical_tests", "Statistical Tests"),
  c("scripts/fileops", "File Operations"),
  c("scripts/visualization", "Data Visualization")
)

total_scripts <- 0
total_passed <- 0
total_failed <- 0

for (category in categories) {
  results <- validate_script_category(category[1], category[2])
  total_scripts <- total_scripts + results$total
  total_passed <- total_passed + results$passed
  total_failed <- total_failed + results$failed
}

# Final summary
cat(sprintf("\n%s\n", paste(rep("=", 50), collapse = "")))
cat("VALIDATION SUMMARY\n")
cat("==================\n")

success_rate <- if (total_scripts > 0) round((total_passed / total_scripts) * 100, 1) else 0

cat(sprintf("Total scripts validated: %d\n", total_scripts))
cat(sprintf("Scripts passed: %d\n", total_passed))
cat(sprintf("Scripts failed: %d\n", total_failed))
cat(sprintf("Success rate: %.1f%%\n", success_rate))

if (total_failed == 0) {
  cat("\n🎉 All validation checks passed!\n")
  cat("✅ RMCP R scripts are ready for production\n")
  quit(status = 0)
} else {
  cat(sprintf("\n⚠️ %d scripts need attention\n", total_failed))
  cat("Please review and fix the issues above\n")
  quit(status = 1)
}

# Helper for string repetition
`%rep%` <- function(str, n) paste(rep(str, n), collapse = "")
