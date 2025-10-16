# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
RMCP (R Model Context Protocol) is a statistical analysis server that bridges AI assistants with R statistical computing capabilities through the Model Context Protocol.

## Development Commands

### Setup & Running
```bash
poetry install                    # Install dependencies
poetry run rmcp start            # Start server in stdio mode
poetry run rmcp http             # Start HTTP server with SSE
```

### Testing
```bash
pytest tests/unit/               # Run unit tests (no R required)
pytest tests/integration/        # Run integration tests (requires R)
pytest tests/e2e/               # Run end-to-end tests
pytest -xvs tests/test_file.py::test_name  # Run single test
```

### Code Quality
```bash
black rmcp tests streamlit       # Format code
isort rmcp tests streamlit       # Sort imports
flake8 rmcp tests streamlit      # Lint code
mypy rmcp                        # Type checking
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

## Important Notes
- Python 3.10+ required
- R must be installed for integration/E2E tests
- All R communication uses JSON via subprocess
- HTTP transport includes session management and SSE for streaming
- VFS security restricts file access to configured paths only