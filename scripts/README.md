# RMCP Scripts Directory

This directory contains development and testing scripts organized by purpose:

## Directory Structure

```
scripts/
├── README.md              # This file
├── manage.py              # Script management utility
├── testing/               # Testing orchestration scripts
│   ├── run_e2e_tests.py  # Main E2E testing suite
│   ├── test-local.sh     # Local Docker testing script
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

## Script Categories

### Testing Scripts (`testing/`)

Scripts that orchestrate testing workflows, validation, and CI/CD preparation.

**`run_e2e_tests.py`** - Main E2E Testing Suite
- **Purpose**: Comprehensive testing across all environments
- **Usage**: `python scripts/testing/run_e2e_tests.py [--quick|--claude|--docker|--performance|--all]`
- **Features**:
  - Local environment validation
  - Real Claude Desktop integration testing
  - Docker workflow validation
  - Performance benchmarking
  - Cross-platform compatibility checks
- **Dependencies**: Python 3.10+, Docker (optional), Claude Desktop (optional)

**`test-local.sh`** - Local Docker Testing
- **Purpose**: Fast local validation using Docker
- **Usage**: `./scripts/testing/test-local.sh`
- **Features**:
  - Python linting (black, isort, flake8)
  - R script syntax validation
  - MCP server integration testing
  - Unit test execution
  - CI/CD preparation validation
- **Dependencies**: Docker

### Debugging Scripts (`debugging/`)

Scripts for diagnosing issues and investigating problems.

**`debug-mcp-protocol.sh`** - MCP Protocol Debugging
- **Purpose**: Debug MCP protocol communication issues
- **Usage**: `./scripts/debugging/debug-mcp-protocol.sh`
- **Features**:
  - R integration verification
  - CLI command testing
  - MCP protocol communication debugging
  - Server creation diagnostics
- **Dependencies**: Docker

### Integration Scripts (`testing/integration/`)

Real-world integration testing that requires external services and can't run in CI/CD.

**`claude_desktop_e2e.py`** - Real Claude Desktop Integration
- **Purpose**: Test actual Claude Desktop integration
- **Usage**: `python scripts/testing/integration/claude_desktop_e2e.py`
- **Features**: Real Claude Desktop communication, MCP protocol validation
- **Dependencies**: Claude Desktop, Python 3.10+

**`docker_workflows.py`** - Docker Workflow Validation  
- **Purpose**: Complete Docker workflow testing
- **Usage**: `python scripts/testing/integration/docker_workflows.py`
- **Features**: Full Docker environment validation, statistical workflows
- **Dependencies**: Docker, Python 3.10+

### Setup Scripts (`setup/`)

Local environment setup, validation, and configuration automation.

**`validate_local_setup.py`** - Local Environment Validation
- **Purpose**: Validate and auto-fix local development environment
- **Usage**: `python scripts/setup/validate_local_setup.py [--auto-fix]`
- **Features**: 
  - Python, R, Docker environment checks
  - Claude Desktop configuration validation
  - IDE integration testing
  - Auto-fix capabilities
- **Dependencies**: Python 3.10+

**`setup_automation.py`** - Automated Environment Setup
- **Purpose**: Automated setup for new users and development environments
- **Usage**: `python scripts/setup/setup_automation.py [--all]`
- **Features**:
  - Claude Desktop auto-configuration
  - VS Code + Continue extension setup
  - Docker environment configuration
  - R package installation
- **Dependencies**: Python 3.10+

### Development Scripts (`development/`)

Utility scripts for development workflows (reserved for future use).

## Script Lifecycle Management

### Creation Guidelines

1. **Purpose**: Each script should have a single, clear purpose
2. **Documentation**: Include usage, dependencies, and examples
3. **Error Handling**: Robust error handling and informative messages
4. **Testing**: Scripts should be testable and include validation
5. **Portability**: Consider cross-platform compatibility

### Maintenance Policies

1. **Regular Review**: Scripts reviewed quarterly for relevance
2. **Deprecation**: Mark outdated scripts before removal
3. **Dependencies**: Document and validate all dependencies
4. **Performance**: Monitor execution time and optimize as needed

### Naming Conventions

- Use kebab-case for shell scripts: `test-local.sh`
- Use snake_case for Python scripts: `run_e2e_tests.py`
- Include purpose in name: `debug-mcp-protocol.sh`
- Avoid abbreviations unless widely understood

## Usage Guidelines

### Running Scripts

1. **From Project Root**: Always run scripts from the project root directory
2. **Permissions**: Ensure shell scripts are executable: `chmod +x scripts/testing/test-local.sh`
3. **Dependencies**: Verify dependencies before running
4. **Environment**: Use appropriate Python environment (poetry, venv, etc.)

### Examples

```bash
# Quick validation
python scripts/testing/run_e2e_tests.py --quick

# Full local testing with Docker
./scripts/testing/test-local.sh

# Debug MCP protocol issues
./scripts/debugging/debug-mcp-protocol.sh

# Complete E2E validation
python scripts/testing/run_e2e_tests.py --all
```

## CI/CD Integration

Scripts are integrated into CI/CD workflows:

1. **Pre-commit**: Linting and basic validation
2. **Pull Request**: Full test suite execution
3. **Release**: Comprehensive validation across environments
4. **Monitoring**: Performance and reliability tracking

## Contributing

When adding new scripts:

1. Choose appropriate directory based on purpose
2. Follow naming conventions and documentation standards
3. Include usage examples and dependency information
4. Test script thoroughly before committing
5. Update this README with script information

## Troubleshooting

### Common Issues

**Script not found**: Ensure you're running from project root
**Permission denied**: Make shell scripts executable with `chmod +x`
**Docker not available**: Install Docker or skip Docker-dependent tests
**R environment issues**: Verify R installation and package availability

### Getting Help

1. Check script documentation (`--help` flag where available)
2. Review error messages and logs
3. Run debugging scripts for specific issues
4. Consult project documentation in `docs/`