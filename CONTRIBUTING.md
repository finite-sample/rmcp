# Contributing to RMCP

We welcome contributions to RMCP! This document provides guidelines for contributing to the project.

## 🚀 Quick Start for Contributors

### Prerequisites

- **Python 3.8+**
- **R 4.0+** with required packages
- **Git**
- **Poetry** (recommended) or pip

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/rmcp.git
   cd rmcp
   ```

2. **Set up Python environment with Poetry (recommended)**
   ```bash
   # Install Poetry if you haven't already
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Install dependencies
   poetry install --with dev
   
   # Activate virtual environment
   poetry shell
   ```

3. **Install R packages**
   ```r
   # In R console
   install.packages(c(
     "jsonlite", "plm", "lmtest", "sandwich", "AER", "dplyr",
     "forecast", "vars", "urca", "tseries", "nortest", "car",
     "rpart", "randomForest", "ggplot2", "gridExtra", "tidyr", "rlang"
   ), repos = "https://cran.rstudio.com/")
   ```

4. **Verify installation**
   ```bash
   # Test RMCP works
   rmcp --version
   rmcp list-capabilities
   
   # Run tests
   python run_tests.py
   ```

## 📋 Types of Contributions

### 🐛 Bug Reports
- Use GitHub Issues with the "bug" label
- Include reproduction steps, expected vs actual behavior
- Provide system information (Python version, R version, OS)

### ✨ Feature Requests
- Use GitHub Issues with the "enhancement" label
- Describe the use case and proposed solution
- Consider if it fits RMCP's scope (statistical analysis via MCP)

### 🔧 Code Contributions
- Bug fixes
- New statistical tools
- Performance improvements
- Documentation improvements

### 📚 Documentation
- README improvements
- API documentation
- Usage examples
- Troubleshooting guides

## 🛠️ Development Workflow

### 1. **Creating a Branch**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 2. **Making Changes**

#### Code Style
We use automated formatting and linting:

```bash
# Format code
poetry run black rmcp tests
poetry run isort rmcp tests

# Check linting
poetry run flake8 rmcp tests
poetry run mypy rmcp
```

#### Pre-commit Hooks (Recommended)
```bash
poetry run pre-commit install
# Now hooks run automatically on commit
```

### 3. **Testing**

Run comprehensive tests before submitting:

```bash
# Run all tests
python run_tests.py

# Run specific test categories
python tests/unit/test_new_tools.py           # Unit tests
python tests/integration/test_mcp_interface.py  # Integration tests
python tests/e2e/realistic_scenarios.py      # End-to-end tests

# Run with pytest (if available)
poetry run pytest tests/unit/ -v
```

### 4. **Committing Changes**

```bash
git add .
git commit -m "feat: add new statistical tool for time series analysis"
# or
git commit -m "fix: resolve import error in tools module"
```

**Commit Message Format:**
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions/modifications
- `refactor:` Code refactoring
- `style:` Code style changes

### 5. **Submitting Pull Request**

1. Push your branch: `git push origin your-branch-name`
2. Create Pull Request on GitHub
3. Fill out the PR template
4. Wait for review and address feedback

## 🔧 Adding New Statistical Tools

### Tool Structure

Create new tools in `rmcp/tools/` following this pattern:

```python
from typing import Dict, Any
from ..tools.common import execute_r_script

async def your_tool(context, params) -> Dict[str, Any]:
    """
    Brief description of what this tool does.
    
    Args:
        context: MCP context
        params: Dict with keys:
            - data: Dict of column_name -> values
            - your_param: Description
    
    Returns:
        Dict with analysis results
    """
    
    # Parameter validation
    data = params.get('data', {})
    your_param = params.get('your_param', 'default')
    
    if not data:
        raise ValueError("Data is required")
    
    # R script
    r_script = f'''
    # Load required libraries
    library(jsonlite)
    
    # Your R analysis code here
    result <- list(
        analysis_output = your_analysis,
        metadata = list(rows = nrow(df))
    )
    
    writeLines(toJSON(result, auto_unbox = TRUE), con = stdout())
    '''
    
    return await execute_r_script(context, r_script, {"data": data, "param": your_param})

# Tool registration happens in rmcp/cli.py
```

### Tool Guidelines

1. **Validation**: Always validate input parameters
2. **Error Handling**: Provide clear error messages
3. **Documentation**: Include comprehensive docstrings
4. **R Libraries**: Check required R packages are documented
5. **Testing**: Add tests in appropriate test files
6. **Metadata**: Include analysis metadata in results

### Registering Tools

Add your tool to `rmcp/cli.py` in the `_register_builtin_tools` function:

```python
register_tool_functions(
    server.tools,
    # ... existing tools ...
    your_tool
)
```

## 🧪 Testing Guidelines

### Test Categories

1. **Unit Tests** (`tests/unit/`): Test individual functions
2. **Integration Tests** (`tests/integration/`): Test MCP protocol integration
3. **End-to-End Tests** (`tests/e2e/`): Test realistic user scenarios

### Writing Tests

```python
import asyncio
import json
from rmcp.core.server import create_server

async def test_your_tool():
    # Create server and register tools
    server = create_server()
    # ... register tools ...
    
    # Test data
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "your_tool",
            "arguments": {
                "data": {"x": [1, 2, 3], "y": [4, 5, 6]},
                "your_param": "test_value"
            }
        }
    }
    
    # Execute
    response = await server.handle_request(request)
    result = json.loads(response['result']['content'][0]['text'])
    
    # Assertions
    assert 'analysis_output' in result
    print("✅ your_tool test passed")

if __name__ == "__main__":
    asyncio.run(test_your_tool())
```

## 📝 Documentation Standards

### Code Documentation
- Use comprehensive docstrings for all public functions
- Include parameter types and descriptions
- Provide usage examples where helpful

### README Updates
- Update tool counts if adding new tools
- Add examples for significant new features
- Keep installation instructions current

## 🔍 Code Review Process

### What We Look For

1. **Functionality**: Does it work as intended?
2. **Code Quality**: Is it readable, maintainable?
3. **Testing**: Are there adequate tests?
4. **Documentation**: Is it properly documented?
5. **Performance**: Does it handle data efficiently?
6. **Security**: Are R scripts safe and validated?

### Review Checklist

- [ ] Code follows style guidelines (Black, isort)
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] No hardcoded values or secrets
- [ ] Error handling is appropriate
- [ ] R script security is considered

## 🚨 Security Considerations

### R Script Safety
- Never execute user-provided R code directly
- Validate all inputs before passing to R
- Use controlled R environment
- Avoid file system operations unless necessary

### Input Validation
- Validate all user inputs
- Check data types and ranges
- Sanitize strings passed to R

## 🎯 Release Process

### Version Numbering
We follow Semantic Versioning (semver):
- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backwards compatible
- **Patch** (0.0.1): Bug fixes, backwards compatible

### Release Checklist
- [ ] All tests pass
- [ ] Version numbers are consistent
- [ ] Changelog is updated
- [ ] Documentation reflects changes
- [ ] Performance benchmarks pass

## 💬 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check README and troubleshooting guides

## 🙏 Recognition

Contributors are recognized in:
- Release notes
- GitHub contributors page
- Special recognition for significant contributions

## 📜 License

By contributing to RMCP, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to RMCP! 🎉