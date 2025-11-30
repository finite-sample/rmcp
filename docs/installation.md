# Installation

```{include} ../README.md
:start-after: "### 🖥️ **Or Install Locally**"
:end-before: "## ✨ What Can RMCP Do?"
```

## Development Installation

For development, clone the repository and install with uv:

```bash
git clone https://github.com/finite-sample/rmcp.git
cd rmcp
uv sync --group dev
```

## Docker Installation

Use the pre-built Docker image for a complete R + Python environment:

```bash
docker build -f docker/Dockerfile --target development -t rmcp-dev .
docker run -v $(pwd):/workspace -it rmcp-dev bash
# Inside container:
cd /workspace && pip install -e .
rmcp start
```

## R Dependencies

RMCP requires R packages for statistical analysis. The Docker approach includes all R packages. For local installation, R dependencies are managed automatically through the security whitelist system.

Check which tools are available:

```bash
rmcp list-capabilities
```

## Verification

Verify the installation works:

```bash
# Check version
rmcp --version

# List available tools (should show 53 tools)
rmcp list-capabilities

# Start the server
rmcp start
```
