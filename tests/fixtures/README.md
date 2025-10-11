# RMCP Testing Approach

## Simple and Direct Testing

RMCP uses a straightforward testing approach:

**✅ Tests run actual R when testing R integration**
- No complex mocking or fixtures for R integration tests
- Tests use real R scripts with real data
- Catches actual integration issues immediately
- Simple and maintainable

## Test Types

### Unit Tests
- Test R integration tools: Run actual R with `pytest.mark.skipif` when R unavailable
- Test pure Python logic: No R needed, test Python code directly
- Located in `tests/unit/`

### Integration Tests  
- Test full MCP protocol with real R execution
- Located in `tests/integration/`

### E2E Tests
- Test complete user workflows
- Located in `tests/e2e/`

## When R is Not Available

Tests automatically skip when R is not installed:
```python
pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for these tests"
)
```

## Key Benefits

1. **Simple**: No complex mocking infrastructure to maintain
2. **Accurate**: Tests the actual R integration, not simulated behavior  
3. **Fast**: R scripts execute quickly in tests
4. **Reliable**: Catches real integration issues immediately
5. **Maintainable**: Changes to R scripts are immediately reflected in tests

## Fixtures (Rarely Needed)

The `load_r_fixture()` function exists for special cases where pre-captured R outputs are needed (e.g., testing error handling). Most tests should run actual R instead.

## Guidelines

- ✅ **Do**: Run actual R in tests that test R integration
- ✅ **Do**: Use `pytest.mark.skipif` when R might not be available
- ✅ **Do**: Keep tests simple and direct
- ❌ **Don't**: Mock R execution unless testing specific error conditions
- ❌ **Don't**: Create complex fixture systems for normal testing