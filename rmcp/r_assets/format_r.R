#!/usr/bin/env Rscript
#' RMCP R Code Formatting Script
#'
#' Automatically formats RMCP R statistical analysis scripts and utility functions
#' using the styler package with consistent style guidelines.

# Check if styler is available
if (!requireNamespace("styler", quietly = TRUE)) {
  cat("styler package is required but not installed.\n")
  cat("Installing styler...\n")
  install.packages("styler", repos = "https://cran.r-project.org")
}

library(styler)

# Set working directory to r_assets
script_dir <- dirname(normalizePath(sys.frame(1)$ofile))
setwd(script_dir)

cat("RMCP R Code Formatter\n")
cat("====================\n")
cat(sprintf("Working directory: %s\n", getwd()))
cat(sprintf("styler version: %s\n", packageVersion("styler")))
cat("\n")

# Define custom style guide for RMCP
rmcp_style <- function() {
  # Start with tidyverse style as base
  style <- tidyverse_style()

  # Customize for our needs
  style$line_break$remove_line_breaks_in_fun_dec <- TRUE
  style$indention$indent_by <- 2L
  style$space$remove_space_before_closing_paren <- TRUE
  style$space$remove_space_before_opening_paren <- FALSE
  style$line_break$remove_line_breaks <- TRUE

  return(style)
}

# Function to format specific files or directories
format_files <- function(paths, title, dry_run = FALSE) {
  cat(sprintf("Formatting %s%s...\n", title, if (dry_run) " (dry run)" else ""))

  formatted_count <- 0
  error_count <- 0

  for (path in paths) {
    if (file.exists(path)) {
      if (file.info(path)$isdir) {
        # Format all R files in directory
        r_files <- list.files(path, pattern = "\\.R$", recursive = TRUE, full.names = TRUE)
        cat(sprintf("Found %d R files in %s\n", length(r_files), path))

        for (r_file in r_files) {
          tryCatch(
            {
              if (dry_run) {
                # Check if file needs formatting
                needs_styling <- !styler::style_file(r_file,
                  style = rmcp_style,
                  dry = "on"
                )
                if (needs_styling) {
                  cat(sprintf("  📝 %s needs formatting\n", basename(r_file)))
                  formatted_count <- formatted_count + 1
                } else {
                  cat(sprintf("  ✅ %s already well formatted\n", basename(r_file)))
                }
              } else {
                # Actually format the file
                result <- styler::style_file(r_file, style = rmcp_style)
                if (any(result$changed)) {
                  cat(sprintf("  📝 Formatted %s\n", basename(r_file)))
                  formatted_count <- formatted_count + 1
                } else {
                  cat(sprintf("  ✅ %s (no changes needed)\n", basename(r_file)))
                }
              }
            },
            error = function(e) {
              cat(sprintf("  ❌ Error formatting %s: %s\n", basename(r_file), e$message))
              error_count <- error_count + 1
            }
          )
        }
      } else {
        # Format single file
        tryCatch(
          {
            if (dry_run) {
              needs_styling <- !styler::style_file(path, style = rmcp_style, dry = "on")
              if (needs_styling) {
                cat(sprintf("  📝 %s needs formatting\n", basename(path)))
                formatted_count <- formatted_count + 1
              } else {
                cat(sprintf("  ✅ %s already well formatted\n", basename(path)))
              }
            } else {
              result <- styler::style_file(path, style = rmcp_style)
              if (any(result$changed)) {
                cat(sprintf("  📝 Formatted %s\n", basename(path)))
                formatted_count <- formatted_count + 1
              } else {
                cat(sprintf("  ✅ %s (no changes needed)\n", basename(path)))
              }
            }
          },
          error = function(e) {
            cat(sprintf("  ❌ Error formatting %s: %s\n", basename(path), e$message))
            error_count <- error_count + 1
          }
        )
      }
    } else {
      cat(sprintf("⚠️ Path not found: %s\n", path))
    }
  }

  return(list(formatted = formatted_count, errors = error_count))
}

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)
dry_run <- "--dry-run" %in% args || "--check" %in% args
verbose <- "--verbose" %in% args

if (dry_run) {
  cat("🔍 Running in dry-run mode (checking formatting only)\n\n")
}

# Format utility functions
cat("1. Processing utility functions...\n")
utils_results <- format_files(c("R/utils.R"), "utility functions", dry_run)

# Format test files
cat("\n2. Processing test files...\n")
test_results <- format_files(c("tests/testthat"), "test files", dry_run)

# Format selected statistical scripts
cat("\n3. Processing statistical scripts (sample)...\n")
script_paths <- c(
  "scripts/descriptive/summary_stats.R",
  "scripts/regression/linear_model.R",
  "scripts/timeseries/arima_model.R",
  "scripts/machine_learning/kmeans_clustering.R",
  "scripts/fileops/read_csv.R"
)
scripts_results <- format_files(script_paths, "statistical scripts", dry_run)

# Summary
total_formatted <- utils_results$formatted + test_results$formatted + scripts_results$formatted
total_errors <- utils_results$errors + test_results$errors + scripts_results$errors

cat(sprintf("\n%s\n", paste(rep("=", 50), collapse = "")))
cat("FORMATTING SUMMARY\n")
cat("==================\n")

if (dry_run) {
  if (total_formatted == 0) {
    cat("🎉 All files are properly formatted!\n")
    cat("✅ No formatting changes needed\n")
  } else {
    cat(sprintf("📝 %d files need formatting\n", total_formatted))
    cat("Run without --dry-run to apply changes\n")
  }
} else {
  if (total_formatted == 0) {
    cat("🎉 All files were already properly formatted!\n")
    cat("✅ No changes were necessary\n")
  } else {
    cat(sprintf("📝 Successfully formatted %d files\n", total_formatted))
    cat("✅ Code now follows RMCP style guidelines\n")
  }
}

if (total_errors > 0) {
  cat(sprintf("⚠️ %d files had formatting errors\n", total_errors))
}

cat("\nStyle guidelines applied:\n")
cat("- Tidyverse style as base\n")
cat("- 2-space indentation\n")
cat("- Consistent spacing around operators\n")
cat("- Proper line breaks and function formatting\n")
cat("- Snake_case for variable and function names\n")

# Exit with appropriate code
if (dry_run) {
  exit_code <- if (total_formatted > 0) 1 else 0
} else {
  exit_code <- if (total_errors > 0) 1 else 0
}

quit(status = exit_code)
