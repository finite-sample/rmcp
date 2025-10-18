# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
RMCP (R Model Context Protocol) is a statistical analysis server that bridges AI assistants with R statistical computing capabilities through the Model Context Protocol.

## Development Commands

### Setup & Running (Hybrid Approach)

**For Python-only development (cross-platform):**
```bash
poetry install --with dev        # Install minimal Python dependencies
poetry run rmcp start            # Start server in stdio mode (no R tools)
poetry run rmcp http             # Start HTTP server with SSE
```

**For R integration development (Docker-based):**
```bash
docker build -f docker/Dockerfile --target development -t rmcp-dev .  # Build R + Python dev environment
docker run -v $(pwd):/workspace -it rmcp-dev bash
# Inside container:
cd /workspace && pip install -e .
rmcp start                        # Full R integration available
```

**For production deployment (optimized):**
```bash
docker build -f docker/Dockerfile --target production -t rmcp-production .  # Multi-stage optimized build
docker run -p 8000:8000 rmcp-production rmcp http                          # Production HTTP server
```

### Testing (Hybrid Strategy)

**Python-only tests (cross-platform via Poetry):**
```bash
poetry run pytest tests/unit/    # Schema validation, JSON-RPC, transport
poetry run black --check .       # Code formatting
poetry run isort --check .       # Import sorting
poetry run flake8 .              # Linting
```

**Complete integration tests (Docker-based):**
```bash
# Docker includes R + FastAPI for complete test coverage (all 201 tests)
docker run -v $(pwd):/workspace rmcp-dev bash -c "cd /workspace && pip install -e . && pytest tests/integration/"
docker run -v $(pwd):/workspace rmcp-dev bash -c "cd /workspace && pip install -e . && pytest tests/scenarios/"
# Full test suite: smoke + unit + integration + scenarios + protocol
docker run -v $(pwd):/workspace rmcp-dev bash -c "cd /workspace && pip install -e . && pytest tests/"
```

### Code Quality
```bash
# Python formatting (cross-platform)
poetry run black rmcp tests streamlit
poetry run isort rmcp tests streamlit  
poetry run flake8 rmcp tests streamlit
poetry run mypy rmcp

# R formatting (Docker-based)
docker run -v $(pwd):/workspace rmcp-dev R -e "library(styler); style_file(list.files('rmcp/r_assets', pattern='[.]R$', recursive=TRUE, full.names=TRUE))"
```

## Architecture

### Core Components
- **Transport Layer** (`rmcp/transport/`): Handles stdio and HTTP+SSE communication
- **Core Server** (`rmcp/core/`): MCPServer, Context management, JSON-RPC protocol
- **Registries** (`rmcp/registries/`): Dynamic registration for tools, resources, prompts
- **Tools** (`rmcp/tools/`): 44 statistical analysis tools across 11 categories
- **R Integration** (`rmcp/r_integration.py`): Python-R bridge via subprocess + JSON

### Adding New Statistical Tools
1. Create tool function in appropriate file under `rmcp/tools/`
2. Use `@tool` decorator with input/output JSON schemas
3. Implement corresponding R script in `r_assets/scripts/`
4. Write schema validation tests in `tests/unit/tools/` (Python-only)
5. Write functional tests in `tests/integration/tools/` (real R execution)
6. Add scenario tests in `tests/scenarios/` for user workflows

### Key Design Patterns
- **Registry Pattern**: All tools/resources/prompts use centralized registries
- **Context Pattern**: Request-scoped state management with lifecycle
- **Transport Abstraction**: Common interface for stdio/HTTP transports
- **Virtual Filesystem**: Security sandbox for file operations (`rmcp/security/vfs.py`)

### Testing Strategy (Optimized Organization)

**Tier 1: Basic Functionality (Python-only, cross-platform)**
- **Smoke tests** (`tests/smoke/`): Basic server startup, CLI, imports (no R required, very fast)
- **Unit tests** (`tests/unit/`): Pure Python logic organized by component:
  - `tests/unit/core/`: Server, context, schemas
  - `tests/unit/tools/`: Tool schema validation
  - `tests/unit/transport/`: HTTP transport logic

**Tier 2: Integration Testing (R + FastAPI required, Docker-based)**
- **Protocol tests** (`tests/integration/protocol/`): MCP protocol validation with mocked R responses
- **Tool integration** (`tests/integration/tools/`): Real R execution for statistical tool functionality
- **Transport integration** (`tests/integration/transport/`): HTTP transport with real FastAPI server
- **Core integration** (`tests/integration/core/`): Server registries, capabilities, error handling

**Tier 3: Complete User Scenarios (End-to-end)**
- **Scenario tests** (`tests/scenarios/`): Full user workflows and deployment scenarios:
  - `test_realistic_scenarios.py`: Statistical analysis pipelines  
  - `test_claude_desktop_scenarios.py`: Claude Desktop integration flows (includes concurrent load testing)
  - `test_excel_plotting_scenarios.py`: File workflow scenarios
  - `test_deployment_scenarios.py`: Docker environment validation, production builds, multi-platform testing

**Development Utilities**
- **`scripts/testing/run_comprehensive_tests.py`**: Comprehensive test runner for development (tests all 44 tools with real R)

**Complete Test Coverage**: Docker environment includes **all 201 tests** with comprehensive coverage across all components:
- ✅ **R Integration**: 44 statistical tools with real R execution  
- ✅ **HTTP Transport**: FastAPI, uvicorn, SSE streaming, session management
- ✅ **Core MCP Protocol**: JSON-RPC 2.0, tool calls, capabilities, error handling
- ✅ **Production Deployment**: Multi-stage Docker builds, security validation, size optimization
- ✅ **Scalability**: Concurrent request handling, load testing, performance validation
- ✅ **Cross-platform**: Multi-architecture support, numerical consistency, platform compatibility
- ✅ **Zero Skipped Tests**: All 201 tests execute successfully with no dependency-related skips

**Strategy**: Tests progress from basic functionality → protocol compliance → component integration → complete scenarios. Each tier builds on the previous, ensuring fast feedback for basic issues while providing comprehensive validation for complex workflows.

## Hybrid Development Approach

**Why Hybrid?**
- **Docker**: Ensures consistent R environment for integration testing (complex R package dependencies)
- **Poetry**: Enables cross-platform Python testing on Mac/Windows/Linux (important for CLI tools)
- **Optimized**: No 179KB `poetry.lock` in repository (regenerated locally as needed)
- **Flexible**: Developers can choose lightweight Poetry setup or full Docker environment

**When to use what:**
- **Local development**: Poetry for Python development, schema changes, CLI testing
- **R tool development**: Docker for testing actual R integration and statistical computations
- **CI/CD**: Docker for R tests, Poetry for cross-platform Python validation

## Important Notes
- Python 3.11+ required
- R environment provided via Docker (no local R installation needed for development)
- All R communication uses JSON via subprocess
- HTTP transport includes session management and SSE for streaming
- VFS security restricts file access to configured paths only
- `poetry.lock` is gitignored (optimizes repository size, regenerated locally)