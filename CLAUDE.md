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
docker build -t rmcp-dev .       # Build R + Python environment
docker run -v $(pwd):/workspace -it rmcp-dev bash
# Inside container:
cd /workspace && pip install -e .
rmcp start                        # Full R integration available
```

### Testing (Hybrid Strategy)

**Python-only tests (cross-platform via Poetry):**
```bash
poetry run pytest tests/unit/    # Schema validation, JSON-RPC, transport
poetry run black --check .       # Code formatting
poetry run isort --check .       # Import sorting
poetry run flake8 .              # Linting
```

**R integration tests (Docker-based):**
```bash
docker run -v $(pwd):/workspace rmcp-dev bash -c "cd /workspace && pip install -e . && pytest tests/integration/"
docker run -v $(pwd):/workspace rmcp-dev bash -c "cd /workspace && pip install -e . && pytest tests/workflow/"
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
5. Write functional tests in `tests/integration/` (real R execution)
6. Add workflow tests in `tests/workflow/` for user scenarios

### Key Design Patterns
- **Registry Pattern**: All tools/resources/prompts use centralized registries
- **Context Pattern**: Request-scoped state management with lifecycle
- **Transport Abstraction**: Common interface for stdio/HTTP transports
- **Virtual Filesystem**: Security sandbox for file operations (`rmcp/security/vfs.py`)

### Testing Strategy
- **Unit tests** (`tests/unit/`): Pure Python logic - schema validation, JSON-RPC protocol, transport layer (no R required)
- **Integration tests** (`tests/integration/`): Real R execution for tool functionality, error handling, MCP protocol compliance
- **Workflow tests** (`tests/workflow/`): End-to-end user scenarios with real R analysis pipelines
- **Smoke tests** (`tests/smoke/`): Basic functionality validation across all tools
- **E2E tests** (`tests/e2e/`): Full MCP protocol flows with Claude Desktop simulation
- **Deployment tests** (`tests/deployment/`): Docker environment and CI/CD validation

**Unified Real R Strategy**: Since R is available in all environments (development, CI/CD), tests use real R execution instead of mocks for accuracy and reliability. This eliminates mock maintenance and ensures tests validate actual behavior.

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