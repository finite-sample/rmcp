# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RMCP is a Model Context Protocol (MCP) server that provides comprehensive statistical analysis capabilities through R. **Version 0.3.6** includes 40 statistical analysis tools across 9 categories, enabling AI assistants to perform sophisticated statistical modeling, econometric analysis, machine learning, time series analysis, and data science tasks through natural conversation.

## Key Architecture Components

### Core Server Architecture
- **FastMCP Server**: Custom MCP implementation in `rmcp/server/fastmcp.py` that handles protocol communication
- **STDIO Interface**: Located in `rmcp/server/stdio.py`, manages standard input/output communication with MCP clients
- **CLI Interface**: `rmcp/cli.py` provides command-line interface with `start`, `version` commands

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
# Check version (should show 0.3.6)
rmcp --version

# Start server (auto-detects MCP protocol vs legacy JSON)
rmcp start

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

## Recent Improvements (v0.3.6)

### Package Release Readiness
- **Version Consistency**: All files updated to v0.3.6 (pyproject.toml, CLI, README, CITATION.cff)
- **Package Structure**: Added missing `rmcp/tools/__init__.py` for proper imports
- **Dependency Cleanup**: Removed problematic `subprocess32` dependency (Python 3.8+ compatibility)
- **Distribution Ready**: Added `MANIFEST.in` for proper package distribution

### Enhanced Tool Ecosystem
- **40 Statistical Tools**: Expanded from 39 to 40 tools across 9 categories
- **Natural Language Features**: Formula builder converts natural language to R formulas
- **Error Recovery System**: Intelligent error diagnosis and automated suggestions
- **Example Datasets**: Built-in datasets for learning and testing

### Testing & Quality Assurance
- **Comprehensive Error Handling**: Added `test_error_handling.py` with 9 error scenarios
- **Organized Test Structure**: Unit → Integration → E2E test organization
- **Cross-Platform Support**: Fixed hardcoded Python commands for compatibility
- **Production Testing**: 100% success rate for realistic user scenarios

### Documentation & Contributing
- **Professional Documentation**: Created comprehensive `CONTRIBUTING.md`
- **Development Guidelines**: Code style, testing procedures, tool development guide
- **Security Considerations**: Safe R script execution guidelines
- **PyPI Distribution**: Package now available via `pip install rmcp`

### GitHub Integration
- **Automated Workflows**: CI/CD pipeline with comprehensive testing
- **Version Verification**: Automated checks for tool count and version consistency
- **Multi-Python Testing**: Support for Python 3.8-3.11

## Configuration Files

- `pyproject.toml`: Poetry configuration with package metadata and CLI entry points
- `requirements.txt`: Python testing dependencies (pytest)
- `Dockerfile`: Multi-stage build with R base image, installs R packages and Python dependencies