# RMCP R Statistical Analysis Package

This directory contains the R statistical analysis infrastructure for the RMCP (R Model Context Protocol) server. It provides a comprehensive set of statistical analysis capabilities through a well-organized R package structure.

## Package Structure

```
rmcp/r_assets/
├── DESCRIPTION              # R package metadata and dependencies
├── NAMESPACE               # Package exports and imports
├── .Rbuildignore          # Files to ignore during R package build
├── .lintr                 # Linting configuration
├── R/                     # R package source code
│   └── utils.R           # Shared utility functions
├── scripts/              # Statistical analysis scripts (44 tools across 11 categories)
│   ├── descriptive/      # Summary statistics, frequency tables, outlier detection
│   ├── regression/       # Linear models, correlation, logistic regression
│   ├── timeseries/       # ARIMA, decomposition, stationarity tests
│   ├── machine_learning/ # K-means, decision trees, random forests
│   ├── statistical_tests/# t-tests, ANOVA, chi-square, normality tests
│   ├── fileops/          # CSV/Excel/JSON reading and writing
│   ├── visualization/    # Plots, charts, correlation heatmaps
│   ├── econometrics/     # Panel regression, instrumental variables, VAR
│   ├── transforms/       # Data transformations, standardization
│   ├── formula_builder/  # Dynamic formula construction
│   └── helpers/          # Error analysis, example datasets
├── tests/                # Test suite
│   ├── testthat.R       # Test runner configuration
│   └── testthat/        # Individual test files
├── man/                  # Generated documentation (via roxygen2)
├── docs/                 # Package website (via pkgdown)
└── Tool Scripts:
    ├── run_tests.R       # Run testthat test suite
    ├── build_docs.R      # Generate roxygen2 documentation
    ├── lint_r.R          # Run lintr code analysis
    ├── format_r.R        # Apply styler code formatting
    └── validate_r.R      # Comprehensive validation pipeline
```

## Quick Start

### Prerequisites

Ensure you have R 4.0+ installed with the following packages:

```r
# Core dependencies
install.packages(c("jsonlite", "dplyr", "ggplot2"))

# Statistical packages
install.packages(c("forecast", "broom", "cluster", "rpart", "randomForest"))

# Econometrics packages
install.packages(c("plm", "lmtest", "sandwich", "AER", "vars"))

# Development tools
install.packages(c("testthat", "roxygen2", "lintr", "styler", "devtools"))
```

### Running Individual Tools

R scripts are designed to work through the RMCP template system, which provides automatic argument parsing, utility functions, and output formatting. For direct testing, use the Python loader:

```python
# Example: Run linear regression through template system
from rmcp.r_assets.loader import get_r_script
import subprocess, tempfile

script_content = get_r_script('regression', 'linear_model')
with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
    f.write(script_content)
    result = subprocess.run(['Rscript', f.name, '{"data": {"x": [1,2,3,4,5], "y": [2,4,6,8,10]}, "formula": "y ~ x"}'], capture_output=True, text=True)
    print(result.stdout)
```

**Note**: Raw R scripts in `scripts/` contain only statistical logic and require the template system for execution.

### Quality Assurance Tools

```bash
# Run all tests
./run_tests.R

# Check code formatting
./format_r.R --dry-run    # Check formatting
./format_r.R              # Apply formatting

# Run linting
./lint_r.R

# Generate documentation
./build_docs.R

# Complete validation pipeline
./validate_r.R            # Full validation
./validate_r.R --quick    # Quick syntax and format check
```

## Development Workflow

### 1. Code Quality Standards

- **Style**: Follows tidyverse style guidelines via styler
- **Linting**: Uses lintr with customized rules for statistical scripts
- **Testing**: Comprehensive testthat suite covering all tool categories
- **Documentation**: roxygen2 documentation for all functions

### 2. Adding New Statistical Tools

1. Create the R script in the appropriate `scripts/` subdirectory
2. Follow the JSON input/output interface pattern
3. Use utility functions from `R/utils.R`
4. Add comprehensive tests in `tests/testthat/`
5. Document with roxygen2 comments
6. Run validation pipeline

Example script structure:

```r
#!/usr/bin/env Rscript
# Load required packages
library(jsonlite)
source(file.path(dirname(sys.frame(1)$ofile), "..", "R", "utils.R"))

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)
if (length(args) == 0) {
  stop("Usage: Rscript script.R '{\"data\": {...}}'")
}

# Parse JSON input
input_data <- fromJSON(args[1])

# Validate input
params <- validate_json_input(input_data, required = c("data"))

# Perform analysis
tryCatch({
  # Your statistical analysis here
  result <- your_analysis_function(params$data)

  # Format output
  output <- format_json_output(
    result = result,
    summary = "Analysis completed successfully"
  )

  # Output JSON
  cat(safe_json(output))

}, error = function(e) {
  # Error handling
  error_output <- list(
    error = TRUE,
    message = e$message,
    type = "analysis_error"
  )
  cat(safe_json(error_output))
  quit(status = 1)
})
```

### 3. Testing Strategy

- **Unit tests**: Individual script functionality
- **Integration tests**: JSON interface compliance
- **Validation tests**: Statistical correctness
- **Performance tests**: Resource usage and timing

### 4. Continuous Integration

The R package integrates with the main RMCP CI/CD pipeline:

```yaml
# In .github/workflows/ci.yml
- name: Validate R Scripts
  run: |
    cd rmcp/r_assets
    ./validate_r.R

- name: Run R Tests
  run: |
    cd rmcp/r_assets
    ./run_tests.R
```

## Architecture

### Core Components

1. **Utility Functions** (`R/utils.R`):
   - `rmcp_progress()`: Progress reporting for long operations
   - `validate_json_input()`: Input parameter validation
   - `format_json_output()`: Consistent output formatting
   - `safe_json()`: Robust JSON serialization
   - `check_packages()`: Dependency verification

2. **Statistical Scripts** (`scripts/`):
   - 44 statistical analysis tools across 11 categories
   - Consistent JSON input/output interface
   - Comprehensive error handling
   - Progress reporting for long operations

3. **Testing Infrastructure** (`tests/`):
   - Category-based test organization
   - Mock data generation
   - Statistical validation
   - Interface compliance testing

### Design Principles

- **Modularity**: Each script is self-contained and independent
- **Consistency**: Uniform JSON interface across all tools
- **Robustness**: Comprehensive error handling and validation
- **Performance**: Efficient algorithms and resource management
- **Maintainability**: Clean code structure with extensive documentation

## Integration with Python MCP Server

The R package integrates seamlessly with the Python MCP server:

1. **Tool Registration**: Python automatically discovers and registers R tools
2. **Execution**: Python spawns R processes with JSON communication
3. **Error Handling**: Structured error responses with helpful messages
4. **Progress Reporting**: Real-time feedback for long-running operations
5. **Security**: Sandboxed execution with controlled file system access

## Statistical Capabilities

### Descriptive Statistics
- Summary statistics with multiple measures
- Frequency tables and cross-tabulations
- Outlier detection using multiple methods

### Regression Analysis
- Linear and logistic regression
- Correlation analysis with multiple methods
- Model diagnostics and validation

### Time Series Analysis
- ARIMA modeling with automatic parameter selection
- Time series decomposition (additive/multiplicative)
- Stationarity testing (ADF, KPSS)

### Machine Learning
- K-means clustering with multiple initialization methods
- Decision trees for classification and regression
- Random forests with variable importance

### Statistical Tests
- t-tests (one-sample, two-sample, paired)
- ANOVA (one-way, factorial)
- Chi-square tests for independence
- Normality tests (Shapiro-Wilk, Kolmogorov-Smirnov)

### Data Visualization
- Scatter plots, histograms, box plots
- Time series plots with trend lines
- Correlation heatmaps
- Regression diagnostic plots

### Econometrics
- Panel data regression (fixed/random effects)
- Instrumental variables estimation
- Vector autoregression (VAR) models

## Contributing

1. Follow the established code style and testing patterns
2. Add comprehensive tests for new functionality
3. Update documentation for any interface changes
4. Run the full validation pipeline before submitting changes
5. Ensure all statistical outputs include appropriate metadata

## License

This R package is part of the RMCP project and follows the same licensing terms.
