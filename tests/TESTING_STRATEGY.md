# RMCP Testing Strategy: Unified Real R Approach

## Overview

RMCP uses a **Unified Real R Testing Strategy** that eliminates mocks in favor of real R execution across all test levels. This approach ensures test accuracy, reduces maintenance overhead, and provides consistent behavior validation.

## Why Real R Everywhere?

### The Foundational Question
**"Why do we need mocks when we always have access to R?"**

This question led to a fundamental architecture simplification:

1. **R is Always Available**: Development and CI environments both have R pre-installed
2. **Mocks Create Drift**: Fake R responses can become outdated as R behavior changes
3. **Real Behavior is Better**: Actual R errors, warnings, and edge cases provide accurate testing
4. **Simpler Architecture**: One testing strategy instead of maintaining parallel mock/real systems

### Benefits
- **Accuracy**: Tests validate actual R behavior, not assumptions
- **Reliability**: No mock drift or outdated fake responses
- **Simplicity**: Single testing approach across all environments
- **Comprehensive**: Real R errors and warnings are captured
- **Maintenance**: No mock synchronization required

## Test Structure

### Unit Tests (`tests/unit/`)
**Purpose**: Pure Python logic validation - no R required

**Contents**:
- Schema validation for tool inputs/outputs
- JSON-RPC protocol compliance
- MCP server core functionality
- Transport layer (HTTP, stdio)
- Registry pattern validation

**Characteristics**:
- Fast execution (< 1 second)
- No external dependencies
- Cross-platform compatible
- Schema-focused testing using realistic data patterns

### Integration Tests (`tests/integration/`)
**Purpose**: Real R execution for tool functionality

**Contents**:
- All statistical tools with real R execution
- Error handling with actual R errors
- MCP protocol compliance with R integration
- Resource registry functionality
- File operations with real filesystem

**Characteristics**:
- Real R subprocess execution
- Actual error scenario testing
- Complete Python↔R pipeline validation
- Docker environment compatible

### Workflow Tests (`tests/workflow/`)
**Purpose**: End-to-end user scenarios

**Contents**:
- Complete analysis workflows
- Claude Desktop simulation
- Error recovery scenarios
- Multi-tool pipelines
- Realistic business use cases

**Characteristics**:
- User experience focused
- Real data scenarios
- Full MCP protocol flows
- Error-to-recovery workflows

### Smoke Tests (`tests/smoke/`)
**Purpose**: Basic functionality validation

**Contents**:
- All tools basic execution
- Quick health checks
- Installation validation
- Environment verification

### E2E Tests (`tests/e2e/`)
**Purpose**: Full system integration

**Contents**:
- Claude Desktop scenarios
- Complete MCP client simulation
- Production-like environments

### Deployment Tests (`tests/deployment/`)
**Purpose**: Infrastructure validation

**Contents**:
- Docker environment testing
- CI/CD pipeline validation
- Cross-platform compatibility

## Test Organization Principles

### Clear Separation by Dependencies
- **Unit**: Python-only (jsonschema, pytest, etc.)
- **Integration+**: Requires R installation
- **Workflow**: Requires R + realistic datasets
- **E2E**: Requires R + MCP client simulation

### Realistic Data Usage
All tests use **R-validated realistic data** instead of artificial patterns:

**Good** (realistic business data):
```python
data = {
    "sales": [120, 135, 128, 142, 156, 148, 160, 175],
    "marketing": [10, 12, 11, 14, 16, 15, 17, 18]
}
# R validation: R² = 0.985, p < 0.001
```

**Bad** (artificial perfect correlation):
```python
data = {
    "x": [1, 2, 3, 4],
    "y": [1, 2, 3, 4]  # r = 1.0 (unrealistic)
}
```

### Error Testing Philosophy
Instead of mocking errors, tests trigger **real R error conditions**:

```python
# Real R error from insufficient data
insufficient_data = {"x": [1], "y": [2]}  # Only 1 observation
result = await linear_model(context, {"data": insufficient_data, "formula": "y ~ x"})
# R naturally fails with "insufficient observations" error
```

## Running Tests

### Development (Local)
```bash
# Unit tests (fast, Python-only)
pytest tests/unit/ -v

# Integration tests (requires R)
pytest tests/integration/ -v

# All tests
pytest tests/ -v
```

### CI/CD (Docker)
```bash
# Full test suite in Docker environment
pytest tests/unit/ tests/integration/ tests/workflow/ tests/smoke/ -v --cov=rmcp
```

### Test Categories by Speed
1. **Unit** (~1-10 seconds): Schema validation, Python logic
2. **Integration** (~30-60 seconds): R tool execution
3. **Workflow** (~60-120 seconds): Multi-tool scenarios
4. **Smoke** (~30 seconds): Basic functionality
5. **E2E** (~120+ seconds): Full system scenarios

## Migration from Mock-Based Testing

### What Was Eliminated
1. **Mocked R execution**: `monkeypatch.setattr("rmcp.tools.*.execute_r_script_async", fake_*)`
2. **Artificial error scenarios**: Fake R errors instead of real conditions
3. **Unit/Integration confusion**: Tests that claimed to be "unit" but required R
4. **Mock maintenance**: Keeping fake responses synchronized with R changes

### What Was Preserved
1. **Schema validation**: Pure Python testing of JSON schema compliance
2. **Protocol testing**: MCP/JSON-RPC format validation
3. **Fast feedback**: Unit tests still provide quick validation
4. **Test organization**: Clear separation by actual dependencies

## Best Practices

### Writing New Tests

1. **Start with Unit Tests** for pure Python logic
2. **Add Integration Tests** for R functionality
3. **Include Workflow Tests** for user scenarios
4. **Use realistic data** validated through actual R execution
5. **Test error conditions** with real R error triggers

### Test Data Standards
- All mock data must be **R-validated realistic patterns**
- Business scenarios preferred over mathematical abstractions
- Document R validation results as comments
- Use consistent variable naming (sales, marketing, revenue, etc.)

### Error Testing Approach
- Use real R conditions that naturally produce errors
- Test complete error-to-recovery workflows
- Validate error message quality for end users
- Ensure errors provide actionable guidance

## Conclusion

The Unified Real R Testing Strategy simplifies RMCP testing by eliminating artificial boundaries and mock maintenance. By using real R execution everywhere it's needed, tests provide accurate validation of actual behavior while maintaining clear separation between Python-only and R-dependent functionality.

This approach aligns with the foundational insight that **"if R is always available, why not use it?"** - leading to simpler, more reliable, and more accurate testing.