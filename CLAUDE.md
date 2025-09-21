# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RMCP is a Model Context Protocol (MCP) server that provides comprehensive statistical analysis capabilities through R. **Version 0.3.8** includes 40 statistical analysis tools across 9 categories, enabling AI assistants to perform sophisticated statistical modeling, econometric analysis, machine learning, time series analysis, and data science tasks through natural conversation.

## Key Architecture Components

### Core Server Architecture
- **FastMCP Server**: Custom MCP implementation in `rmcp/server/fastmcp.py` that handles protocol communication
- **STDIO Interface**: Located in `rmcp/server/stdio.py`, manages standard input/output communication with MCP clients (primary transport for Claude Desktop)
- **HTTP Interface**: Located in `rmcp/transport/http.py`, provides HTTP/SSE transport for web applications and custom integrations
- **CLI Interface**: `rmcp/cli.py` provides command-line interface with `start`, `serve-http`, `version` commands

### Tool System (40 Tools Across 9 Categories)
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

#### Natural Language & User Experience (NEW)
- **Formula Builder** (`rmcp/tools/formula_builder.py`): Convert natural language to R formulas, validate formulas
- **Error Recovery** (`rmcp/tools/helpers.py`): Intelligent error diagnosis, data validation, example datasets

### Transport Layer
- **STDIO Transport** (`rmcp/transport/stdio.py`): Primary transport for Claude Desktop integration
- **HTTP Transport** (`rmcp/transport/http.py`): FastAPI-based HTTP server with the following endpoints:
  - `POST /`: JSON-RPC 2.0 requests (all 40 statistical tools available)
  - `GET /sse`: Server-Sent Events for real-time notifications
  - `GET /health`: Health check endpoint for monitoring
  - CORS support for web applications
  - Async request handling with proper error responses

### R Integration
- **Common Utilities** (`rmcp/tools/common.py`): Contains `execute_r_script()` function that creates temporary files, executes R code, and parses JSON results
- **Required R Packages**: 
  - Core: plm, lmtest, sandwich, AER, jsonlite, dplyr
  - Advanced: forecast, vars, urca, ggplot2, gridExtra, tidyr, rlang
- All data exchange between Python and R happens via JSON serialization
- Enhanced error handling with custom `RExecutionError` class for detailed diagnostics

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
# Check version (should show 0.3.8)
rmcp --version

# Start stdio server (for Claude Desktop integration)
rmcp start

# Start HTTP server (for web applications and custom clients)
rmcp serve-http --port 8080

# List available tools (should show 40 tools)
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

## Tool Registration Pattern

Tools are registered in `rmcp/cli.py` using the `_register_builtin_tools` function. All 40 tools are imported and registered automatically:

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
        # ... all 40 tools ...
    )
    logger.info("Registered comprehensive statistical analysis tools (40 total)")
```

## R Script Execution Flow

1. Python tool function receives parameters
2. `execute_r_script()` creates temporary files for R script, arguments, and results
3. R script loads required libraries, reads JSON args, performs analysis
4. Results written to JSON file and returned to Python
5. Temporary files cleaned up

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
- **40 Statistical Tools**: Complete ecosystem across 9 categories
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
   - Tool count verification (40 tools)
   - New features testing
   - Documentation consistency checks

### Docker Optimization (`Dockerfile.ci`)
```dockerfile
FROM python:3.11-slim
# Pre-installs all R packages (22 packages)
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