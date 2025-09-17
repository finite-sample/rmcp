# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.6] - 2025-09-17

### Added
- **PyPI Distribution**: Package now available via `pip install rmcp`
- **Enhanced Error Handling**: Comprehensive error handling test suite with 9 scenarios
- **Contributing Guidelines**: Professional `CONTRIBUTING.md` with development workflow
- **Natural Language Features**: Formula builder converts descriptions to R formulas
- **Error Recovery System**: Intelligent error diagnosis with automated suggestions
- **Example Datasets**: Built-in datasets for learning and testing (sales, economics, etc.)

### Fixed
- **Package Structure**: Added missing `rmcp/tools/__init__.py` for proper imports
- **Version Consistency**: All files synchronized to v0.3.6 (CLI, README, CITATION.cff)
- **Dependency Issues**: Removed problematic `subprocess32` dependency for Python 3.8+ compatibility
- **Cross-Platform Support**: Fixed hardcoded Python commands in test runner
- **Tool Count Accuracy**: Updated from 39 to 40 tools across all documentation

### Changed
- **Tool Expansion**: Now includes 40 statistical analysis tools across 9 categories
- **Test Organization**: Restructured tests into unit → integration → e2e hierarchy
- **Distribution Ready**: Added `MANIFEST.in` for proper package distribution
- **Documentation Update**: Enhanced CLAUDE.md with current architecture and features

### Security
- **R Script Safety**: Enhanced validation and error handling for R execution
- **Input Sanitization**: Comprehensive input validation across all tools

## [0.3.5] - 2025-09-17

### Fixed
- **Claude Desktop Compatibility**: Fixed MCP protocol version mismatch
  - Updated protocol version from `2024-11-05` to `2025-06-18` to match Claude Desktop expectations
  - Verified end-to-end integration with Claude Desktop works perfectly
  - All 33 statistical tools now accessible through natural conversation

### Added
- **End-to-End Testing**: Comprehensive verification of Claude Desktop integration
  - Confirmed RMCP server starts and loads all 30+ tools successfully
  - Verified R packages installation and functionality
  - Tested actual tool calls from Claude Desktop to RMCP
  - Added working examples for users to test the integration

### Changed
- **Project Structure Cleanup**: Removed unnecessary complexity
  - Eliminated redundant `scripts/` folder - use standard tools directly
  - Converted project to use Poetry for better dependency management
  - Added GitHub Actions CI/CD workflow for automated testing
  - Cleaned up test directory structure and fixed import paths

## [0.3.4] - 2025-09-16

### Changed
- **Package Structure**: Reorganized codebase with standard Python package layout
  - Moved all package code from `src/rmcp/` to `rmcp/` at root level
  - Updated `pyproject.toml` to reflect new package discovery structure
  - Cleaner, more maintainable repository organization following Python best practices

### Added
- **Streamlit Cloud Deployment**: Added complete Streamlit app for cloud deployment
  - Cloud-ready econometric analysis interface with Claude AI integration
  - Sample data generators (economic panel, time series, financial datasets)
  - Basic statistical analysis capabilities using Python/pandas
  - Instructions for deployment on Streamlit Community Cloud
  - Professional UI showcasing RMCP's econometric capabilities

### Fixed
- Updated all configuration files (pyproject.toml, tooling) for new package structure
- Verified package installation and CLI functionality with reorganized codebase

## [0.3.3] - 2025-09-16

### Fixed
- **Critical**: Fixed logger file parameter error that was causing transport startup failures
- **Transport**: Removed invalid `file=sys.stderr` parameters from all logger calls in stdio transport
- **Robustness**: Improved cross-platform compatibility and error handling

### Added
- **Documentation**: Comprehensive troubleshooting guide (docs/troubleshooting.md)
- **Documentation**: Enhanced docstrings throughout codebase with detailed examples
- **Documentation**: Improved README with realistic usage scenarios and conversation examples
- **Documentation**: Added practical examples for all major tool categories

### Improved
- **Developer Experience**: Better error messages and debugging information
- **Maintainability**: Professional-grade documentation standards throughout
- **User Onboarding**: Clear installation and configuration instructions

## [0.1.1] - 2025-08-30

### Added
- **Dual Protocol Support**: Server now supports both legacy JSON format and full MCP protocol with automatic detection
- **Enhanced CLI**: Added `rmcp dev` command for development server testing
- **Comprehensive Testing**: Added unit tests, integration tests, and server tests with >80% coverage
- **Improved Error Handling**: Custom `RExecutionError` class with detailed error information
- **Enhanced Logging**: Structured logging throughout the application with configurable levels
- **Type Definitions**: Added comprehensive type hints and data classes in `rmcp.types`
- **Development Tools**: Added support for black, isort, flake8, mypy, and pytest with coverage

### Changed
- **Tool Registration**: Fixed circular imports and cleaned up tool registration architecture
- **CLI Entry Point**: Updated to use `rmcp.cli:cli` for better structure
- **Package Metadata**: Enhanced pyproject.toml with comprehensive metadata and classifiers
- **Documentation**: Added comprehensive docstrings and improved CLAUDE.md with recent changes
- **Version Consistency**: Synchronized version numbers across all components (0.1.1)

### Fixed
- **R Script Execution**: Enhanced error handling with timeout support and better error messages
- **Tool Discovery**: Fixed issues with tools not being properly registered on import
- **Test Scripts**: Updated all test scripts to use new CLI commands instead of legacy files
- **Circular Imports**: Resolved circular import issues between MCP instance and tool modules

### Security
- **Input Validation**: Added proper input validation and sanitization for R script execution
- **Timeout Protection**: Added 30-second timeout for R script execution to prevent hanging
- **Error Sanitization**: Improved error message handling to avoid information leakage

## [0.1.0] - Initial Release

### Added
- **Core MCP Server**: Basic Model Context Protocol server implementation
- **R Integration**: Execute R scripts for econometric analysis
- **Tool Suite**: 
  - Linear regression (`linear_model`)
  - Panel data analysis (`panel_model`) 
  - Instrumental variables (`iv_regression`)
  - Diagnostic tests (`diagnostics`)
  - Correlation analysis (`correlation`)
  - Group-by operations (`group_by`)
  - File analysis (`analyze_csv`)
- **Docker Support**: Containerized deployment with R dependencies
- **CLI Interface**: Basic command-line interface with `rmcp` command
- **Documentation**: README with usage examples and tool documentation

### Dependencies
- **Python**: Requires Python >=3.8
- **R Packages**: plm, lmtest, sandwich, AER, jsonlite, dplyr
- **Python Packages**: click >=8.1.0

---

## Development Notes

### Testing
Run the test suite:
```bash
# All tests
pytest

# With coverage
pytest --cov=rmcp --cov-report=html

# Specific test files
pytest tests/test_common.py -v
```

### Code Quality
```bash
# Format code
black rmcp tests

# Sort imports  
isort rmcp tests

# Lint code
flake8 rmcp tests

# Type checking
mypy rmcp
```

### Release Process
1. Update version in `rmcp/__init__.py` and `pyproject.toml`
2. Update CHANGELOG.md with new features and fixes
3. Run full test suite: `pytest --cov=rmcp`
4. Run integration tests: `./tests/test_all_tools.sh`
5. Build package: `poetry build`
6. Test package installation: `pip install dist/rmcp-*.whl`
7. Verify CLI: `rmcp version`
8. Create git tag: `git tag v0.1.1`
9. Push: `git push && git push --tags`