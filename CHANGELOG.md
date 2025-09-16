# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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