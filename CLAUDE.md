# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RMCP is a Model Context Protocol (MCP) server that provides comprehensive statistical analysis capabilities through R. **Version 0.3.11** includes 44 statistical analysis tools across 11 categories, enabling AI assistants to perform sophisticated statistical modeling, econometric analysis, machine learning, time series analysis, and data science tasks through natural conversation.

## Key Architecture Components

### Core Server Architecture
- **FastMCP Server**: Custom MCP implementation in `rmcp/server/fastmcp.py` that handles protocol communication
- **STDIO Interface**: Located in `rmcp/server/stdio.py`, manages standard input/output communication with MCP clients (primary transport for Claude Desktop)
- **HTTP Interface**: Located in `rmcp/transport/http.py`, provides HTTP/SSE transport for web applications and custom integrations
- **CLI Interface**: `rmcp/cli.py` provides command-line interface with `start`, `serve-http`, `version` commands

### Tool System (44 Tools Across 11 Categories)
The server implements comprehensive statistical analysis tools as Python functions that execute R scripts:

#### Regression & Correlation Tools
- **Regression Tools** (`rmcp/tools/regression.py`): Linear regression, logistic regression, correlation analysis
- **Econometrics** (`rmcp/tools/econometrics.py`): Panel regression, instrumental variables, VAR models

#### Time Series Analysis
- **Time Series Tools** (`rmcp/tools/timeseries.py`):
  - ARIMA modeling with automatic order selection
  - Time series decomposition (trend, seasonal, remainder)
  - Stationarity testing (ADF, KPSS, Phillips-Perron)

#### Statistical Testing
- **Statistical Tests** (`rmcp/tools/statistical_tests.py`): t-tests, ANOVA, chi-square tests, normality tests

#### Data Analysis & Transformation
- **Descriptive Statistics** (`rmcp/tools/descriptive.py`): Summary statistics, outlier detection, frequency tables
- **Data Transformations** (`rmcp/tools/transforms.py`): 
  - Lag/lead variables for time series
  - Differencing and growth rates
  - Winsorization for outlier treatment
  - Standardization (z-score, min-max, robust)

#### Machine Learning
- **Machine Learning** (`rmcp/tools/machine_learning.py`): K-means clustering, decision trees, random forest

#### Data Visualization
- **Professional Visualizations** (`rmcp/tools/visualization.py`):
  - Scatter plots with trend lines and grouping
  - Time series plots for single/multiple variables
  - Histograms with density overlays
  - Correlation heatmaps
  - Comprehensive residual diagnostic plots

#### File Operations
- **File Operations** (`rmcp/tools/fileops.py`): CSV, Excel, JSON import/export, data filtering, data info

#### Natural Language & User Experience
- **Formula Builder** (`rmcp/tools/formula_builder.py`): Convert natural language to R formulas, validate formulas
- **Error Recovery** (`rmcp/tools/helpers.py`): Intelligent error diagnosis, data validation, example datasets

#### Flexible R Execution (NEW in v0.3.11)
- **Flexible R Analysis** (`rmcp/tools/flexible_r.py`): Execute custom R code with security validation
  - Package whitelist enforcement (45+ allowed packages)
  - Execution timeout limits and memory constraints
  - Audit logging and comprehensive safety features
  - Support for visualization with base64 image encoding

### Transport Layer
- **STDIO Transport** (`rmcp/transport/stdio.py`): Primary transport for Claude Desktop integration
- **HTTP Transport** (`rmcp/transport/http.py`): FastAPI-based HTTP server with the following endpoints:
  - `POST /`: JSON-RPC 2.0 requests (all 44 statistical tools available)
  - `GET /sse`: Server-Sent Events for real-time notifications
  - `GET /health`: Health check endpoint for monitoring
  - CORS support for web applications
  - Async request handling with proper error responses

### R Integration
- **Common Utilities** (`rmcp/tools/common.py`): Contains `execute_r_script()` function that creates temporary files, executes R code, and parses JSON results
- **Required R Packages**: 
  - Core: plm, lmtest, sandwich, AER, jsonlite, dplyr
  - Advanced: forecast, vars, urca, ggplot2, gridExtra, tidyr, rlang
  - Formatting: broom, knitr (for professional markdown output with formatted tables)
  - Flexible R: 45+ packages including MASS, boot, survival, nlme, mgcv, lme4, glmnet, openxlsx
- All data exchange between Python and R happens via JSON serialization
- Enhanced error handling with custom `RExecutionError` class for detailed diagnostics
- **Professional Output Formatting**: All 44 tools include `_formatting` fields with markdown tables and natural language interpretations using broom/knitr packages

## Development Commands

### Setup with Poetry
```bash
# Install dependencies
poetry install

# Install with all optional groups
poetry install --all-extras

# Install development dependencies
poetry install --with dev

# Activate virtual environment
poetry shell
```

### CLI Commands
```bash
# Check version (should show 0.3.11)
rmcp --version

# Start stdio server (for Claude Desktop integration)
rmcp start

# Start HTTP server (for web applications and custom clients)
rmcp serve-http --port 8080

# List available tools (should show 44 tools)
rmcp list-capabilities

# Start with debug logging
rmcp start --log-level DEBUG
```

### Development Scripts (via Poetry)
```bash
# Format code (black + isort)
poetry run format

# Run linting and type checking
poetry run lint

# Run test suite
poetry run test
```

### Testing (Comprehensive Test Suite)
```bash
# Run all tests in organized sequence (unit → integration → e2e)
python run_tests.py

# Run specific test categories
python tests/unit/test_new_tools.py                    # Unit tests
python tests/unit/test_error_handling.py               # Error handling tests
python tests/integration/test_mcp_interface.py         # Integration tests  
python tests/e2e/test_claude_desktop_scenarios.py      # End-to-end tests

# Run pytest (if available)
pytest tests/unit/ -v                                  # Unit tests only
```

### Running the Server
```bash
# Install in development mode with Poetry
poetry install

# Start MCP server via CLI (supports both MCP protocol and legacy JSON)
poetry run rmcp start

# Direct Python execution
poetry run python -m rmcp

# Test with legacy JSON format
cat tests/test_request.json | poetry run rmcp start

# Test with MCP protocol format
cat tests/test_mcp_protocol.json | poetry run rmcp start
```

### Docker Development
```bash
# Build Docker image
docker build -t r-econometrics-mcp .

# Run container
docker run -it r-econometrics-mcp

# Interactive development
docker run -i r-econometrics-mcp
```

## Recent Improvements (v0.3.11)

### 🔧 Flexible R Code Execution (NEW)
- **Hybrid Approach**: Combines structured tools with flexible R code execution for maximum versatility
- **Two New Tools**: 
  - `execute_r_analysis`: Execute custom R code for advanced analyses with comprehensive safety features
  - `list_allowed_r_packages`: List ~80 whitelisted R packages by category (stats, ml, econometrics, visualization, data)
- **Security Features**: Package whitelist enforcement, execution timeouts, audit logging, dangerous pattern blocking
- **Usage Guidelines**: Use structured tools for common analyses, flexible execution for novel statistical methods and custom workflows

### 🔧 Professional Output Formatting
- **Formatted Statistical Output**: All 44 tools now provide professionally formatted results using broom and knitr packages
  - Markdown tables for statistical summaries using `knitr::kable()`
  - Tidy statistical results using `broom::tidy()`, `broom::glance()`, and `broom::augment()`
  - Natural language interpretations of statistical results
  - Schema-safe formatting via `_formatting` fields (extracted before validation)

### 🐛 Critical Bug Fixes
- **Fixed knitr_kable JSON Serialization**: Resolved "No method asJSON S3 class: knitr_kable" error
  - Wrapped all `knitr::kable()` calls with `as.character()` for proper JSON serialization
  - Fixed unbalanced parentheses from automated replacements across all tool files
  - All 44 tools now work correctly with formatted output

- **Fixed File Operations Schema Issues**: Resolved schema validation failures in file import tools
  - Updated `sample_data` schema to accept both objects and arrays
  - Fixed `missing_values` and `column_types` to return proper named lists using `as.list()`
  - All file operations (CSV, Excel, JSON) now validate correctly

### 🧪 Test Suite Improvements  
- **100% Test Success Rate**: All unit, integration, and end-to-end tests now pass
  - Fixed e2e scenario that was failing due to schema validation
  - Comprehensive test coverage across all 44 statistical tools
  - Reliable CI/CD pipeline with consistent results

### 📊 Code Quality & Maintenance
- **Dependency Management**: Added broom and knitr as required R packages for consistent formatting
- **Code Formatting**: Applied black formatting across all Python files
- **Documentation**: Streamlined README.md from 720 to 213 lines (70% reduction) for better user experience
- **Linting Compliance**: Achieved 0 flake8 errors across entire codebase
  - Fixed unused imports, variables, and f-strings without placeholders
  - Resolved all line length issues (E501) for consistent code style
  - All black, isort, and flake8 checks now pass in CI/CD
- **Documentation Synchronization**: Automated docs/index.rst to pull content from README.md
  - Uses MyST parser to include README.md directly in Sphinx documentation
  - Eliminates manual synchronization between README and documentation
  - Documentation builds properly ignore _build/ artifacts via .gitignore

## Previous Improvements (v0.3.10)

### 🔧 Enhanced Flexibility
- **Output Schema Validation**: Made optional for increased flexibility
  - Tools now work with varying output formats without validation errors
  - Input validation preserved to catch user errors
  - Improves compatibility with evolving R package outputs

### 📊 Bug Fixes
- **Correlation Analysis**: Fixed economist scenario test indexing
  - Corrected correlation matrix access from numeric to key-based
  - All 4 realistic E2E scenarios now pass (100% success)
- **Data Transformation**: Fixed array serialization in R scripts
  - `winsorize` tool: Added `I()` wrapper for proper JSON arrays
  - `decompose_timeseries`: Fixed NA handling in R script execution

### 🚀 CI/CD Improvements  
- **Response Structure**: Updated tool response format
  - JSON data now properly structured in `structuredContent`
  - Maintains backward compatibility with legacy formats
  - Fixed CI test extraction for new response structure

### 🎨 Code Quality
- **Import Organization**: Applied comprehensive import sorting
  - Fixed import ordering in 31 Python files using isort
  - All linting checks pass (black, isort, flake8)
  - 100% test success rate across all categories

### ✅ Production Validation
- **Direct R Testing**: Comprehensive validation of statistical capabilities
  - Linear regression, time series, machine learning, econometrics
  - Base64 image encoding for inline visualization
  - All 44 tools working correctly across 11 categories

## Tool Registration Pattern

Tools are registered in `rmcp/cli.py` using the `_register_builtin_tools` function. All 44 tools are imported and registered automatically:

```python
# Tools are imported and registered in rmcp/cli.py
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.regression import linear_model, correlation_analysis, logistic_regression
from rmcp.tools.helpers import suggest_fix, validate_data, load_example
# ... all other tools ...

def _register_builtin_tools(server):
    register_tool_functions(
        server.tools,
        linear_model,
        correlation_analysis,
        # ... all 44 tools ...
    )
    logger.info("Registered comprehensive statistical analysis tools (44 total)")
```

## R Script Execution Flow

1. Python tool function receives parameters
2. `execute_r_script()` creates temporary files for R script, arguments, and results
3. R script loads required libraries, reads JSON args, performs analysis
4. Results written to JSON file and returned to Python
5. Temporary files cleaned up

## Hybrid Approach: Structured Tools + Flexible R Execution

### When to Use Each Approach

**Use Structured Tools For:**
- Standard statistical analyses (regression, correlation, t-tests, ANOVA)
- Common data transformations (lag, difference, standardization, winsorization)
- File operations (CSV, Excel, JSON import/export)
- Standard visualizations (scatter plots, histograms, time series plots)
- Well-defined econometric models (panel regression, VAR, instrumental variables)

**Use Flexible R Execution For:**
- Novel statistical methods not covered by structured tools
- Complex custom analyses requiring multiple R packages
- Advanced data manipulations beyond standard transformations
- Custom visualizations with specific formatting requirements
- Experimental statistical techniques or cutting-edge methods
- Analyses requiring specific R package combinations

### Flexible R Execution Guidelines

```python
# Example: Custom multilevel modeling analysis
execute_r_analysis(
    r_code="""
    library(lme4)
    library(broom.mixed)
    
    # Convert to data frame and fit mixed-effects model
    df <- as.data.frame(data)
    model <- lmer(outcome ~ treatment + (1|subject), data = df)
    
    result <- list(
        fixed_effects = tidy(model, effects = "fixed"),
        random_effects = tidy(model, effects = "ran_vals"),
        model_summary = glance(model),
        fitted_values = fitted(model)
    )
    """,
    data={"outcome": [...], "treatment": [...], "subject": [...]},
    packages=["lme4", "broom"],
    description="Multilevel model with random intercepts",
    timeout_seconds=120
)
```

### Security Features

- **Package Whitelist**: Only ~80 approved statistical/data packages allowed
- **Timeout Protection**: Maximum execution time configurable (default 60s, max 300s)
- **Pattern Blocking**: Dangerous patterns like `system()`, `file.remove()` automatically blocked
- **Audit Logging**: All custom R code execution logged for security review
- **Memory Limits**: R options set to prevent memory exhaustion

### Best Practices

1. **Start with Structured Tools**: Always check if a structured tool exists for your analysis
2. **Validate Packages**: Use `list_allowed_r_packages()` to check package availability
3. **Test Incrementally**: Start with simple R code and build complexity gradually  
4. **Handle Errors Gracefully**: Include error checking in your R code
5. **Document Purpose**: Always provide clear description of analysis intent

## Key Integration Points

- **MCP Client Communication**: Uses stdin/stdout JSON messaging protocol
- **R Package Dependencies**: Server requires specific R packages installed in environment
- **Error Handling**: R script failures are captured and returned as JSON error responses
- **Data Validation**: Input schemas defined for each tool to validate parameters

## Recent Improvements (v0.3.7)

### 🚀 CI/CD Infrastructure Optimization
- **Docker-Optimized CI**: Integrated Docker build into CI workflow with proper job dependencies
- **75-85% Speedup**: Pre-built Docker images with all R packages reduce CI time from 5+ minutes to ~2 minutes
- **GitHub Actions Cache**: Docker layer caching for efficient builds
- **100% Test Success**: All unit, integration, and end-to-end tests now passing consistently
- **Container-First Testing**: R dependencies pre-installed in CI environment for reliability

### 📈 Visual Analytics Revolution
- **Inline Image Display**: All 6 visualization tools now display plots directly in Claude conversations
- **Base64 Encoding**: Professional-quality PNG images appear instantly without file management
- **Multi-content MCP Responses**: Support for text + image content in single responses
- **Publication Quality**: ggplot2-styled visualizations ready for presentations
- **Configurable Settings**: Width, height, and quality parameters for all plots
- **Backward Compatibility**: Optional file saving maintained with `file_path` parameter

### 🔧 Data Format Standardization
- **Column-wise JSON Standard**: All tools now return data in `{col1: [values], col2: [values]}` format
- **Schema Validation**: Consistent use of `table_schema()` for data validation
- **Cross-tool Compatibility**: Fixed data format mismatches between load_example, read_json, and validation tools
- **R Script Optimization**: Using `as.list(data)` for proper JSON serialization

### Enhanced Visualization Tools
- **🔥 correlation_heatmap**: Color-coded matrices with inline statistical analysis
- **📈 scatter_plot**: Trend lines and grouping with immediate visual feedback  
- **📊 histogram**: Distribution analysis with density overlays displayed inline
- **📦 boxplot**: Quartile analysis and outlier detection with visual confirmation
- **⏱️ time_series_plot**: Trend analysis with forecasting visualized instantly
- **🔍 regression_plot**: 4-panel diagnostic plots for model validation

### Package Modernization
- **Simplified Packaging**: Removed redundant MANIFEST.in, using modern pyproject.toml-only approach
- **GitHub URL Consistency**: Standardized all URLs to finite-sample/rmcp repository
- **Version 0.3.7**: All files synchronized with new release version
- **Python 3.9+ Requirement**: Aligned all documentation with actual requirements
- **CI/CD Quality Assurance**: Comprehensive testing without pre-commit complexity

### Integration Test Fixes
- **Robust Error Handling**: Fixed JSON parsing errors in test suite
- **Empty Result Handling**: Tools now return valid responses for all scenarios
- **Defensive JSON Parsing**: Improved test reliability and error reporting
- **Helper Tool Reliability**: Enhanced suggest_fix, validate_data, load_example functions

### Previous Improvements (v0.3.6)
- **44 Statistical Tools**: Complete ecosystem across 11 categories
- **Natural Language Features**: Formula builder and intelligent error recovery
- **PyPI Distribution**: Professional package available via `pip install rmcp`
- **Comprehensive Testing**: Unit → Integration → E2E test organization
- **Documentation Excellence**: Professional CONTRIBUTING.md and examples

## CI/CD Workflow Architecture

### GitHub Actions Workflow (`.github/workflows/ci.yml`)
The CI/CD pipeline uses an optimized Docker-first approach:

1. **Lint & Smoke Tests** (19s)
   - Code formatting (black, isort, flake8)
   - Basic CLI functionality
   - Non-R dependent unit tests

2. **Docker Build** (29s with cache)
   - Pre-builds Docker image with all R packages
   - Uses GitHub Actions cache for Docker layers
   - Pushes to GitHub Container Registry (ghcr.io)

3. **Full Test Suite** (41s in container)
   - All 22 unit tests using pre-built Docker image
   - 3 integration test workflows
   - 3 end-to-end scenarios

4. **Feature Verification** (27s)
   - Tool count verification (44 tools)
   - New features testing
   - Code-based verification (no longer relies on documentation content)

### Docker Optimization (`Dockerfile.ci`)
```dockerfile
FROM python:3.11-slim
# Pre-installs all R packages (45+ packages including flexible R packages)
# Pre-installs Python dependencies (pytest, black, etc.)
# Cached for subsequent CI runs
```

### Testing Architecture
- **Unit Tests**: Fast, isolated component testing
- **Integration Tests**: Real MCP protocol workflows  
- **End-to-End Tests**: Complete user scenarios with Claude Desktop simulation
- **100% Pass Rate**: All tests consistently passing

## Data Schema Standards

### Column-wise JSON Format
All RMCP tools return data in standardized column-wise format:
```json
{
  "data": {
    "column1": [value1, value2, value3],
    "column2": [value1, value2, value3]
  }
}
```

### Schema Validation
- `table_schema()`: Validates column-wise data format
- `formula_schema()`: Validates R formula strings
- `image_content_schema()`: Validates base64 image content
- Automatic conversion using `as.list(data)` in R scripts

## Configuration Files

- `pyproject.toml`: Poetry configuration with package metadata and CLI entry points
- `Dockerfile.ci`: CI-optimized Docker image with pre-installed R packages
- `Dockerfile`: Multi-stage build with R base image for development
- `.github/workflows/ci.yml`: Integrated CI/CD workflow with Docker optimization
- `.github/workflows/docs.yml`: Automated documentation build and GitHub Pages deployment
- `docs/conf.py`: Sphinx configuration with MyST parser for README.md inclusion
- `docs/index.rst`: Documentation entry point that automatically includes README.md content
- `.gitignore`: Comprehensive patterns including documentation build artifacts (_build/, *.doctree)

## MCP Client Integration

### Claude Desktop Integration
RMCP is configured to work with Claude Desktop via the Model Context Protocol (MCP):

**Configuration Location**: `~/.modelcontext/mcp.json`
```json
[
  {
    "id": "rmcp",
    "command": ["rmcp", "start"],
    "displayName": "R Econometrics",
    "description": "Run econometric analysis in R via MCP",
    "tags": ["statistics", "econometrics", "R"]
  }
]
```

### Cursor IDE Integration
RMCP also works with Cursor IDE through MCP. Recent fixes ensure full compatibility:

**Configuration Location**: `~/.cursor/mcp.json`
```json
{
  "mcpServers": {
    "rmcp": {
      "command": "rmcp",
      "args": ["start"],
      "env": {
        "RMCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Note**: Version 0.3.11+ includes critical fixes for MCP specification compliance, ensuring `structuredContent` returns proper objects instead of arrays, which resolves JSON schema validation issues with Cursor and other MCP clients.