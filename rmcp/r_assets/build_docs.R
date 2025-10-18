#!/usr/bin/env Rscript
#' RMCP R Documentation Builder
#'
#' Generates roxygen2 documentation for RMCP R statistical analysis package.
#' This script can be called from the main Python project or run independently.

# Check required packages
required_packages <- c("roxygen2", "devtools", "pkgdown")
missing_packages <- required_packages[!sapply(required_packages, requireNamespace, quietly = TRUE)]

if (length(missing_packages) > 0) {
  cat("Installing missing documentation packages...\n")
  install.packages(missing_packages, repos = "https://cran.r-project.org")
}

library(roxygen2)
library(devtools)

# Set working directory to r_assets
script_dir <- dirname(normalizePath(sys.frame(1)$ofile))
setwd(script_dir)

cat("RMCP R Documentation Builder\n")
cat("============================\n")
cat(sprintf("Working directory: %s\n", getwd()))
cat(sprintf("roxygen2 version: %s\n", packageVersion("roxygen2")))
cat("\n")

# Generate documentation
cat("Generating roxygen2 documentation...\n")
tryCatch(
  {
    # Document the package
    roxygen2::roxygenise(package.dir = ".", clean = TRUE)
    cat("✅ roxygen2 documentation generated successfully\n")
  },
  error = function(e) {
    cat("❌ Error generating documentation:\n")
    cat(e$message, "\n")
    quit(status = 1)
  }
)

# Generate NAMESPACE and Rd files summary
cat("\nDocumentation Summary:\n")
cat("=====================\n")

# Check NAMESPACE
if (file.exists("NAMESPACE")) {
  namespace_lines <- readLines("NAMESPACE")
  exports <- namespace_lines[grepl("^export", namespace_lines)]
  cat(sprintf("Exported functions: %d\n", length(exports)))
  if (length(exports) > 0) {
    for (export in exports) {
      cat(sprintf("  - %s\n", export))
    }
  }
} else {
  cat("⚠️ NAMESPACE file not found\n")
}

# Check man directory
if (dir.exists("man")) {
  rd_files <- list.files("man", pattern = "\\.Rd$")
  cat(sprintf("Help files generated: %d\n", length(rd_files)))
  if (length(rd_files) > 0) {
    for (rd_file in rd_files) {
      cat(sprintf("  - %s\n", rd_file))
    }
  }
} else {
  cat("⚠️ man directory not found\n")
}

# Optional: Build package website with pkgdown if available
if (requireNamespace("pkgdown", quietly = TRUE)) {
  cat("\nBuilding package website with pkgdown...\n")
  tryCatch(
    {
      pkgdown::build_site(preview = FALSE)
      cat("✅ Package website built successfully\n")
      cat("📖 Documentation available in docs/ directory\n")
    },
    error = function(e) {
      cat("⚠️ pkgdown website build failed (this is optional):\n")
      cat(e$message, "\n")
    }
  )
}

cat("\n✅ Documentation build completed!\n")
