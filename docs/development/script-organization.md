# Script Organization

RMCP follows a clear separation between automated tests and developer tools to maintain CI/CD clarity and development efficiency.

## Overview

The project organizes code validation into two distinct categories:

1. **`tests/`** - Automated tests that run in CI/CD environments
2. **`scripts/`** - Developer tools for local validation and setup

## Directory Structure

### Tests Directory (CI/CD Only)
```
tests/                          # ONLY CI/CD-runnable tests
├── unit/                      # Unit tests with mocks
├── integration/               # Integration tests with controlled environments
├── fixtures/                  # Test data and fixtures  
├── r_scripts/                 # R test scripts
├── conftest.py               # Test configuration
└── utils.py                  # Test utilities
```

**Purpose**: Contains only tests that can run automatically in CI/CD without external dependencies.

**Characteristics**:
- No external service dependencies (Claude Desktop, real Docker workflows)
- Uses mocks and stubs for external integrations
- Fast execution suitable for automated pipelines
- Follows standard testing conventions

### Scripts Directory (Developer Tools)
```
scripts/
├── README.md              # Complete documentation
├── manage.py              # Script management utility
├── testing/               # Testing orchestration
│   ├── run_e2e_tests.py  # Main E2E testing suite
│   ├── test-local.sh     # Local Docker testing
│   └── integration/      # Real-world integration testing
│       ├── claude_desktop_e2e.py    # Real Claude Desktop testing
│       ├── docker_workflows.py      # Docker workflow validation
│       ├── realistic_scenarios.py   # Real-world scenarios
│       ├── claude_desktop_scenarios.py  # Claude Desktop scenarios
│       ├── docker_simulation.py     # Docker simulation testing
│       └── excel_plotting_workflow.py   # Excel plotting workflows
├── debugging/             # Debugging and diagnostic scripts
│   └── debug-mcp-protocol.sh  # MCP protocol debugging
├── setup/                 # Local environment setup and validation
│   ├── validate_local_setup.py     # Local environment validation
│   ├── setup_automation.py         # Automated setup for new users
│   ├── ide_integrations.py         # IDE integration testing
│   └── validate_ide_configs.py     # IDE configuration validation
└── development/           # Development utility scripts
    └── (future scripts)
```

**Purpose**: Contains developer tools for local validation, setup, and real-world testing.

**Characteristics**:
- May require external services (Claude Desktop, Docker, IDEs)
- Manual execution by developers
- Comprehensive real-world validation
- Setup and configuration automation

## Migration Rationale

### Previous Organization Issues

The previous organization mixed automated tests with developer tools:

```
# PROBLEMATIC (old organization)
tests/
├── e2e/                   # ❌ Couldn't run in CI/CD
│   ├── test_real_claude_desktop_e2e.py  # Required real Claude Desktop
│   └── test_docker_full_workflow.py     # Required full Docker setup
└── local/                 # ❌ Not really tests
    ├── validate_local_setup.py          # Local validation tool
    └── setup_automation.py              # Setup automation tool
```

**Problems**:
1. CI/CD confusion - unclear what should run automatically
2. Violated standard testing conventions
3. Mixed concerns between validation and testing
4. Required complex CI exclusion logic

### New Organization Benefits

The new organization provides clear separation:

```
# OPTIMAL (new organization)
tests/                     # ✅ Only CI/CD-compatible tests
├── unit/                  # ✅ Fast, isolated tests
└── integration/           # ✅ Controlled integration tests

scripts/                   # ✅ Developer tools and validation
├── testing/integration/   # ✅ Real-world testing
└── setup/                 # ✅ Environment setup and validation
```

**Benefits**:
1. **Clear Separation**: tests/ = CI/CD, scripts/ = developer tools
2. **Standard Conventions**: Follows typical project organization patterns
3. **CI/CD Clarity**: No confusion about what runs automatically
4. **Developer Experience**: Logical categorization of tools
5. **Maintainability**: Each directory has single, clear purpose

## CI/CD Integration

The CI/CD pipeline validates the organization:

```yaml
# Script validation ensures proper organization
script-validation:
  steps:
    - name: Validate script organization
      run: |
        # Verify no ad hoc scripts in root
        # Verify scripts are in correct directories  
        # Verify old problematic directories are empty
        python3 scripts/manage.py health-check
```

**Test Execution**: CI/CD only runs specific, CI-compatible tests:
- `tests/unit/` - All unit tests
- `tests/integration/test_mcp_protocol_compliance.py` - MCP protocol tests
- `tests/integration/test_mcp_interface.py` - Interface tests
- `tests/integration/test_schema_validation.py` - Schema validation

**Exclusions**: CI/CD does not run `scripts/` directory contents automatically.

## Usage Guidelines

### For Developers

**Running CI-Compatible Tests Locally**:
```bash
# Run the same tests that run in CI/CD
pytest tests/unit/
pytest tests/integration/test_mcp_protocol_compliance.py
```

**Running Real-World Validation**:
```bash
# Use script management utility
python scripts/manage.py list
python scripts/manage.py run validate-local
python scripts/manage.py run claude-desktop-e2e
```

### For CI/CD

**Automated Testing**: Only files in `tests/` directory with specific test runners.

**Script Validation**: Validates script organization and health without executing scripts.

## Best Practices

### When Adding New Code Validation

**Add to `tests/` if**:
- Can run without external service dependencies
- Uses mocks/stubs for external integrations  
- Executes quickly (< 30 seconds)
- Suitable for automated pipeline execution

**Add to `scripts/` if**:
- Requires real external services (Claude Desktop, Docker)
- Intended for manual developer execution
- Provides setup/configuration functionality
- Performs comprehensive real-world validation

### Naming Conventions

**Tests**: Use `test_` prefix, descriptive names
- `test_mcp_protocol_compliance.py`
- `test_schema_validation.py`

**Scripts**: Use descriptive names without `test_` prefix  
- `claude_desktop_e2e.py`
- `validate_local_setup.py`

## Future Enhancements

Planned improvements to maintain this organization:

1. **Automated Validation**: Enhanced CI checks for proper categorization
2. **Documentation Sync**: Automatic documentation updates for new scripts
3. **Dependency Tracking**: Automated dependency validation for scripts
4. **Performance Monitoring**: Execution time tracking for both tests and scripts