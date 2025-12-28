# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
RMCP (R Model Context Protocol) is a statistical analysis server that bridges AI assistants with R statistical computing capabilities through the Model Context Protocol.

## Development Commands

### Setup & Running (Hybrid Approach)

**For Python-only development (cross-platform):**
```bash
uv sync --group dev              # Install minimal Python dependencies
uv run rmcp start                # Start server in stdio mode (no R tools)
uv run rmcp serve-http           # Start HTTP server with SSE

# Use configuration options
uv run rmcp --debug start        # Enable debug mode
uv run rmcp --config config.json start  # Use custom config file
RMCP_LOG_LEVEL=DEBUG uv run rmcp start  # Use environment variables
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

**Python-only tests (cross-platform via uv):**
```bash
uv run pytest tests/unit/        # Schema validation, JSON-RPC, transport
uv run ruff check .              # Linting and import sorting
uv run ruff format --check .     # Code formatting check
```

**Complete integration tests (Docker-based):**
```bash
# Docker includes R + FastAPI for complete test coverage (all 240+ tests)
docker run -v $(pwd):/workspace rmcp-dev bash -c "cd /workspace && pip install -e . && pytest tests/integration/"
docker run -v $(pwd):/workspace rmcp-dev bash -c "cd /workspace && pip install -e . && pytest tests/scenarios/"
# Full test suite: smoke + unit + integration + scenarios + protocol + config
docker run -v $(pwd):/workspace rmcp-dev bash -c "cd /workspace && pip install -e . && pytest tests/"
```

### Code Quality
```bash
# Python formatting (cross-platform)
uv run ruff check --fix .         # Auto-fix linting issues and sort imports
uv run ruff format .              # Format code
uv run mypy rmcp

# R formatting (Docker-based)
docker run -v $(pwd):/workspace rmcp-dev R -e "library(styler); style_file(list.files('rmcp/r_assets', pattern='[.]R$', recursive=TRUE, full.names=TRUE))"

# Documentation building (cross-platform)
uv run sphinx-build docs docs/_build       # Build documentation
uv run sphinx-build -b html docs docs/_build/html  # HTML output
uv run sphinx-autogen docs/**/*.rst        # Generate autosummary stubs
```

## Architecture

### Core Components
- **Transport Layer** (`rmcp/transport/`): Handles stdio and HTTP+SSE communication
- **Core Server** (`rmcp/core/`): MCPServer, Context management, JSON-RPC protocol
- **Registries** (`rmcp/registries/`): Dynamic registration for tools, resources, prompts
- **Tools** (`rmcp/tools/`): 53 statistical analysis tools across 11 categories
- **Comprehensive Package Whitelist**: 429 R packages from CRAN task views with tiered security
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
- **Universal Operation Approval**: User consent system for file operations and package installation

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
- **`scripts/testing/run_comprehensive_tests.py`**: Comprehensive test runner for development (tests all 53 tools with real R)

**Complete Test Coverage**: Docker environment includes **all 240+ tests** with comprehensive coverage across all components:
- ✅ **R Integration**: 53 statistical tools with real R execution
- ✅ **HTTP Transport**: FastAPI, uvicorn, SSE streaming, session management
- ✅ **Core MCP Protocol**: JSON-RPC 2.0, tool calls, capabilities, error handling
- ✅ **Configuration System**: Environment variables, config files, hierarchical loading
- ✅ **Production Deployment**: Multi-stage Docker builds, security validation, size optimization
- ✅ **Scalability**: Concurrent request handling, load testing, performance validation
- ✅ **Cross-platform**: Multi-architecture support, numerical consistency, platform compatibility
- ✅ **Zero Skipped Tests**: All tests execute successfully with no dependency-related skips

**Strategy**: Tests progress from basic functionality → protocol compliance → component integration → complete scenarios. Each tier builds on the previous, ensuring fast feedback for basic issues while providing comprehensive validation for complex workflows.

## Pre-Commit Validation Protocol

**Critical**: Always test in CI-equivalent environments before committing to prevent CI failures.

### Mandatory Pre-Commit Checklist

**Before every commit that touches Docker, CI workflows, or dependencies:**

```bash
# 1. Build and test in actual CI containers (prevents environment drift)
docker build --target development -t rmcp-test:latest .
docker run --rm -v $(pwd):/workspace rmcp-test:latest bash -c "cd /workspace && pip install -e . && pytest tests/smoke/ -v"
docker run --rm -v $(pwd):/workspace rmcp-test:latest bash -c "cd /workspace && pip install -e . && pytest tests/unit/ -v"

# 2. Test dependency compatibility (prevents pytest-asyncio type issues)
docker run --rm rmcp-test:latest python -c "import pytest, pytest_asyncio; print('✅ Dependencies compatible')"
docker run --rm rmcp-test:latest pytest --version

# 3. Verify multi-platform builds work (prevents platform-specific errors)
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.base --cache-to=type=inline .

# 4. Test both fresh and cached build scenarios (prevents workflow logic errors)
# Fresh build scenario:
docker buildx build --no-cache --target development -t rmcp-fresh:latest .
# Cached build scenario:
docker buildx build --target development -t rmcp-cached:latest .
```

### Local CI Simulation

**Test GitHub Actions workflows locally before push:**

```bash
# Install act (GitHub Actions local runner)
# macOS: brew install act
# Linux: curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Test CI workflow locally (requires Docker)
act push -W .github/workflows/ci.yml

# Test specific CI job
act -j python-checks
act -j docker-build

# Test with different scenarios
act push --var GITHUB_REF=refs/heads/main  # Test main branch behavior
act pull_request --var GITHUB_REF=refs/pull/1/merge  # Test PR behavior
```

### Environment Consistency Validation

**Prevent local vs CI environment drift:**

```bash
# 1. Verify Python package versions match between uv and Docker
uv export --no-hashes > requirements-uv.txt
docker run --rm rmcp-test:latest pip freeze > requirements-docker.txt
diff requirements-uv.txt requirements-docker.txt

# 2. Test pytest configuration consistency
uv run pytest --collect-only tests/smoke/ > pytest-uv.log
docker run --rm -v $(pwd):/workspace rmcp-test:latest pytest --collect-only /workspace/tests/smoke/ > pytest-docker.log
diff pytest-uv.log pytest-docker.log

# 3. Validate R environment consistency
docker run --rm rmcp-test:latest R -e "cat('R packages:', length(.packages(all.available=TRUE)), '\n')"
```

### Build Optimization Regression Testing

**Ensure Docker optimizations don't break with changes:**

```bash
# 1. Time build performance (should remain sub-second for cached builds)
time docker build --target development -t rmcp-perf:latest .

# 2. Verify cache effectiveness
docker buildx build --target development --cache-from=type=gha --cache-to=type=gha,mode=max -t rmcp-cache-test:latest .

# 3. Test production build size (should remain optimized)
docker images --filter "reference=rmcp*" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
```

### Workflow Edge Case Testing

**Test GitHub Actions conditional logic before commit:**

```bash
# 1. Test workflow with no Docker-relevant changes (should skip builds)
git checkout -b test-skip-build
echo "# Test comment" >> README.md
git add . && git commit -m "Test: non-docker change"
# Push and verify CI skips Docker builds

# 2. Test workflow with Docker changes (should trigger builds)
git checkout -b test-trigger-build
echo "# Test comment" >> Dockerfile
git add . && git commit -m "Test: docker change"
# Push and verify CI runs Docker builds

# 3. Test attestation logic with both scenarios
# Verify attestation steps only run when should_build=true
```

### Common CI Issue Prevention

**Patterns that prevent typical CI failures:**

1. **Always test with exact CI dependency versions**:
   ```bash
   # Don't just test with latest packages
   docker run --rm rmcp-test:latest pip list | grep pytest
   ```

2. **Validate pytest configuration changes**:
   ```bash
   # Test asyncio_mode setting works
   docker run --rm -v $(pwd):/workspace rmcp-test:latest pytest /workspace/tests/ --collect-only
   ```

3. **Test GitHub Actions conditional steps**:
   ```bash
   # Use act to test both cached and fresh build paths
   act -j docker-build --var should_build=true
   act -j docker-build --var should_build=false
   ```

4. **Verify multi-platform compatibility**:
   ```bash
   # Test both platforms build successfully
   docker buildx build --platform linux/amd64 --load -t test-amd64 .
   docker buildx build --platform linux/arm64 --load -t test-arm64 .
   ```

### Integration with Development Workflow

**When to use this protocol:**

- **Always**: Before committing changes to `Dockerfile*`, `.github/workflows/`, `pyproject.toml`
- **Docker optimizations**: When modifying cache strategies, base images, or build stages
- **Dependency updates**: When upgrading pytest, Python packages, or R packages
- **CI logic changes**: When modifying conditional steps, build matrices, or attestation workflows
- **Pre-release**: Before tagging releases or major feature merges

**Quick validation for minor changes:**
```bash
# Minimal check for small Python changes
docker run --rm -v $(pwd):/workspace rmcp-test:latest bash -c "cd /workspace && pip install -e . && python -c 'import rmcp; print(\"✅ Import OK\")'"
```

This protocol ensures CI failures are caught locally, maintaining the 99%+ build optimization improvements while preventing regression issues.

## Hybrid Development Approach

**Why Hybrid?**
- **Docker**: Ensures consistent R environment for integration testing (complex R package dependencies)
- **uv**: Enables fast cross-platform Python testing on Mac/Windows/Linux (important for CLI tools)
- **Optimized**: No lock file in repository (uv handles dependency resolution efficiently)
- **Flexible**: Developers can choose lightweight uv setup or full Docker environment

**When to use what:**
- **Local development**: uv for Python development, schema changes, CLI testing
- **R tool development**: Docker for testing actual R integration and statistical computations
- **CI/CD**: Docker for R tests, uv for cross-platform Python validation

## Configuration System

RMCP includes a comprehensive configuration management system that supports:

### **Configuration Sources (Priority Order)**
1. **Command-line arguments** (highest priority)
2. **Environment variables** (`RMCP_*` prefix)
3. **User config file** (`~/.rmcp/config.json`)
4. **System config file** (`/etc/rmcp/config.json`)
5. **Built-in defaults** (lowest priority)

### **Development Configuration**
```bash
# Environment variables for development
export RMCP_LOG_LEVEL=DEBUG
export RMCP_HTTP_PORT=9000
export RMCP_R_TIMEOUT=300

# Configuration file for development
echo '{"debug": true, "logging": {"level": "DEBUG"}}' > ~/.rmcp/config.json

# CLI options override everything
uv run rmcp --debug --config custom.json start
```

### **Docker Configuration**
```bash
# Environment variables in Docker
docker run -e RMCP_HTTP_HOST=0.0.0.0 -e RMCP_HTTP_PORT=8000 rmcp:latest

# Mount configuration file
docker run -v $(pwd)/config.json:/etc/rmcp/config.json rmcp:latest
```

### **Testing Configuration**
- **Unit tests**: Configuration module has 40+ tests covering all scenarios
- **Integration tests**: Configuration integration with HTTP/R/VFS components
- **Environment tests**: Validation of all environment variable mappings

**📖 Complete documentation**: Auto-generated from code in `docs/configuration/` (build with `uv run sphinx-build docs docs/_build`)

## Universal Operation Approval System

RMCP v0.5.1 introduces a comprehensive user consent system for security-sensitive operations that require explicit approval.

### **Operation Categories**

The system categorizes operations by security level and impact:

```python
OPERATION_CATEGORIES = {
    "file_operations": {
        "patterns": [r"ggsave\s*\(", r"write\.csv\s*\(", r"write\.table\s*\(", r"writeLines\s*\("],
        "description": "File writing and saving operations",
        "security_level": "medium",
    },
    "package_installation": {
        "patterns": [r"install\.packages"],
        "description": "R package installation from repositories",
        "security_level": "medium",
    },
    "system_operations": {
        "patterns": [r"system\s*\(", r"shell\s*\(", r"Sys\.setenv"],
        "description": "System-level operations and environment changes",
        "security_level": "high",
    },
}
```

### **User Workflow**

1. **Operation Detection**: When R code contains approval-required patterns, execution pauses
2. **User Notification**: Clear description of operation and security implications shown
3. **Approval Decision**: User accepts/denies with session-wide persistence
4. **Execution**: Approved operations proceed, denied operations are blocked
5. **Session Memory**: Decisions persist for the current session to avoid repetitive prompts

### **Security Features**

- **Pattern Matching**: Regex-based detection with negative lookbehind (e.g., allows `ggsave()` but blocks `save()`)
- **VFS Integration**: File operations require both approval AND VFS write permissions
- **Session Tracking**: Approval state maintained per operation category per session
- **Graceful Fallback**: Operations fail safely with clear error messages when denied

### **Usage Examples**

**File Operations (Visualization):**
```r
# Requires approval for file saving
library(ggplot2)
p <- ggplot(data, aes(x=var1, y=var2)) + geom_point()
ggsave("plot.png", plot=p)  # ← Triggers approval request
```

**Package Installation:**
```r
# Requires approval for package installation
install.packages("tidyverse")  # ← Triggers approval request
library(tidyverse)             # ← Proceeds without approval
```

**System Operations:**
```r
# Requires approval for system access
system("ls -la")               # ← Triggers approval request (high security)
Sys.setenv(PATH="/new/path")   # ← Triggers approval request (high security)
```

### **Developer Integration**

**Adding New Operation Categories:**
```python
# In rmcp/tools/flexible_r.py
OPERATION_CATEGORIES["database_operations"] = {
    "patterns": [r"dbConnect\s*\(", r"dbWriteTable\s*\("],
    "description": "Database connection and write operations",
    "security_level": "high",
}
```

**Testing Approval Workflows:**
```python
# Unit tests in tests/unit/tools/test_operation_approval.py
def test_approval_required():
    context = create_test_context()
    code = 'ggsave("test.png")'

    # Should require approval
    result = await validate_r_code(context, code)
    assert result["requires_approval"] is True
    assert result["operation_info"]["category"] == "file_operations"
```

### **Configuration Options**

**Environment Variables:**
```bash
# Disable approval system (for automation/testing)
export RMCP_DISABLE_OPERATION_APPROVAL=true

# Set default approval for specific categories
export RMCP_AUTO_APPROVE_FILE_OPERATIONS=true
```

**Session Configuration:**
```python
# Programmatic approval (for API integrations)
context.approval_state.approve_category("file_operations")
```

This system balances security with usability, ensuring sensitive operations require explicit user consent while maintaining smooth workflows for approved operations.

## Comprehensive R Package Management

RMCP v0.5.1 introduces a **systematic, evidence-based R package whitelist** with **429 packages** from CRAN task views, replacing the previous narrow 117-package list.

### **Package Selection Methodology**

**Evidence-Based Approach**: Packages selected from official CRAN task views:
- **Machine Learning & Statistical Learning** (61 packages): caret, mlr3, randomForest, xgboost, etc.
- **Econometrics** (55 packages): AER, plm, vars, forecast, quantreg, causal inference tools
- **Time Series Analysis** (57 packages): zoo, xts, forecast, fable, prophet, ARIMA models
- **Bayesian Inference** (40 packages): rstan, brms, MCMCpack, coda, BayesFactor
- **Survival Analysis** (36 packages): survival, flexsurv, randomForestSRC, competing risks
- **Tidyverse Ecosystem** (32 packages): dplyr, ggplot2, tidyr, complete data science workflow

**Additional Categories**: Spatial analysis, optimization, meta-analysis, clinical trials, robust statistics, missing data, NLP, experimental design, network analysis.

### **Tiered Security System**

**4-Tier Permission Model** balances functionality with security:

1. **Tier 1 - Auto-Approved (52 packages)**: Core statistical packages
   - Base R, essential tidyverse, fundamental statistical packages
   - Examples: `ggplot2`, `dplyr`, `MASS`, `survival`, `Matrix`

2. **Tier 2 - User Approval (56 packages)**: Extended functionality
   - Popular ML, econometrics, time series packages
   - Examples: `caret`, `randomForest`, `forecast`, `AER`, `rstan`

3. **Tier 3 - Admin Approval (75 packages)**: Specialized/development
   - Advanced ML, development tools, web packages
   - Examples: `xgboost`, `devtools`, `httr`, `tensorflow`

4. **Tier 4 - Blocked (26 packages)**: Security risks
   - System access, external dependencies, compilation tools
   - Examples: `rJava`, `RMySQL`, `processx`, `system` calls

### **Security Assessment**

**Risk Categorization** by security impact:
- **System Access**: 4 packages (R.utils, unix, etc.)
- **Network Access**: 8 packages (curl, httr, etc.)
- **File Operations**: 8 packages (readr, openxlsx, etc.)
- **Code Execution**: 8 packages (Rcpp, devtools, etc.)
- **External Dependencies**: 7 packages (rJava, database drivers, etc.)

**Results**: 413 low-risk packages (96.3%), 4 medium-risk, 12 high-risk

### **Usage Examples**

**List Available Packages**:
```r
# Get comprehensive package summary
list_allowed_r_packages(category = "summary")

# Explore specific categories
list_allowed_r_packages(category = "machine_learning")
list_allowed_r_packages(category = "econometrics")
list_allowed_r_packages(category = "time_series")
```

**Package Categories Available**:
- `base_r`, `core_infrastructure`, `tidyverse`
- `machine_learning`, `econometrics`, `time_series`, `bayesian`
- `survival`, `spatial`, `optimization`, `meta_analysis`
- `clinical_trials`, `robust_stats`, `missing_data`
- `nlp_text`, `data_io`, `experimental_design`, `network_analysis`

### **Benefits of Systematic Approach**

- **6x Expansion**: From 117 to 429 packages (comprehensive coverage)
- **Evidence-Based**: CRAN task views + download statistics + security assessment
- **Systematic**: Organized by statistical domain, not arbitrary selection
- **Maintainable**: Updates track CRAN task view evolution
- **Secure**: Risk-based tiering with approval workflows
- **User-Friendly**: Reduces approval friction for legitimate statistical work

### **Backward Compatibility**

Legacy categories maintained: `stats`, `ml`, `visualization`, `data` map to new comprehensive categories.

## Documentation System

RMCP uses **Sphinx with autodoc** for automatic documentation generation from code docstrings, eliminating manual documentation maintenance.

### **Auto-Generated Documentation**

Documentation is automatically generated from:
- **Configuration models**: Complete API documentation with examples
- **Module docstrings**: Comprehensive module-level documentation
- **Function/class docstrings**: Detailed parameter and return documentation
- **Type hints**: Automatic type documentation from annotations

### **Documentation Commands**

```bash
# Build HTML documentation
uv run sphinx-build -b html docs docs/_build/html

# Build with clean rebuild
uv run sphinx-build -E -a -b html docs docs/_build/html

# Generate autosummary stubs
uv run sphinx-autogen docs/**/*.rst

# Serve documentation locally
cd docs/_build/html && python -m http.server 8080
```

### **Documentation Structure**

- **User Guide**: Installation, quick start, configuration
- **API Reference**: Auto-generated from docstrings
- **Configuration**: Comprehensive configuration documentation
- **Examples**: Real-world usage scenarios

### **Benefits of Autodoc Approach**

- **Single Source of Truth**: Documentation lives in code
- **Always Current**: Auto-updates with code changes
- **Type Safety**: Shows actual type hints and defaults
- **Cross-References**: Automatic linking between components
- **Search Integration**: Full-text search across documentation

**📖 Documentation URL**: `docs/_build/html/index.html` (after building)

## Important Notes
- Python 3.11+ required
- R environment provided via Docker (no local R installation needed for development)
- All R communication uses JSON via subprocess
- HTTP transport includes session management and SSE for streaming
- VFS security restricts file access to configured paths only
- Configuration system supports all deployment scenarios (local, Docker, production)
- `poetry.lock` is gitignored (optimizes repository size, regenerated locally)
