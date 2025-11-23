# Multi-Target Dockerfile for RMCP
# Supports both development and production environments
#
# Usage:
#   Development: docker build --target development -t rmcp:dev .
#   Production:  docker build --target production -t rmcp:prod .

# ============================================================================
# STAGE: Base Environment (Pre-built R environment)
# ============================================================================
FROM ghcr.io/finite-sample/rmcp/rmcp-base:latest AS base

# Base image already contains:
# - rocker/r2u:noble with optimized R package installation
# - All required system dependencies (Python, build tools, SSL, etc.)
# - 50+ R packages for statistical analysis, ML, and visualization  
# - mkcert for HTTPS development
# - Optimized configurations and cleanup

# Verify base image and display info
RUN echo "📦 Using pre-built RMCP base environment" && \
    cat /opt/rmcp-base-info.json && \
    echo "🔍 R packages available: $(R -q --slave -e 'cat(length(.packages(all.available=TRUE)))')" && \
    echo "✅ Base environment ready"

# ============================================================================
# STAGE: Development Environment (Full development stack)
# ============================================================================
FROM base AS development

# Note: R packages and mkcert are already installed in base image

# Install uv for dependency management
ARG TARGETPLATFORM
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-dev-${TARGETPLATFORM} \
    set -eux; \
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Ensure venv tools are first on PATH for subsequent steps/CI
ENV PATH="$VENV/bin:$PATH"

# Development workspace setup
WORKDIR /workspace
ENV PYTHONPATH=/workspace

# Copy source code for development
COPY pyproject.toml ./
# Create a minimal README for build
RUN echo "# RMCP Development Environment" > README.md
COPY rmcp/ ./rmcp/

# Install RMCP and dependencies using uv sync
ENV VIRTUAL_ENV=/workspace/.venv
ENV PATH="/workspace/.venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-dev-sync-${TARGETPLATFORM} \
    set -eux; \
    export PATH="/root/.local/bin:$PATH"; \
    # Install all development dependencies and HTTP extras
    uv sync --group dev --extra all; \
    # Verify installation
    python -c "import rmcp; print('RMCP installed successfully')"

# Default to bash for development work
CMD ["bash"]

# ============================================================================
# STAGE: Production Builder (Optimized build environment)
# ============================================================================
FROM base AS builder

# Install uv for dependency management
ARG TARGETPLATFORM
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-prod-${TARGETPLATFORM} \
    set -eux; \
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy and build RMCP package
WORKDIR /build
# Copy files in order of change frequency (metadata first, then code)
COPY pyproject.toml ./
# Create minimal README.md for build (excluded by .dockerignore)
RUN echo "# RMCP Production Build" > README.md
COPY rmcp/ ./rmcp/
# Install production dependencies and build wheel
ENV VIRTUAL_ENV=/build/.venv
ENV PATH="/build/.venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-build-${TARGETPLATFORM} \
    set -eux; \
    export PATH="/root/.local/bin:$PATH"; \
    # Install production dependencies with HTTP extras (no dev dependencies)
    uv sync --no-group dev --extra all; \
    # Build wheel for production installation
    uv build --wheel --out-dir /build/wheels/

# ============================================================================
# STAGE: Production Runtime (Optimized from base image)
# ============================================================================
FROM base AS production-base

# Remove development tools to minimize size (aggressive cleanup)
RUN set -eux; \
    apt-get remove -y \
        build-essential \
        gcc g++ \
        pkg-config \
        python3-dev \
        git \
        curl; \
    apt-get autoremove -y; \
    apt-get clean; \
    # Clean temporary files
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

# ============================================================================
# STAGE: Production Runtime (Final minimal environment)
# ============================================================================
FROM production-base AS production

ARG TARGETPLATFORM
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Note: Runtime dependencies already installed in production-base
# (python3, python3-venv, libcurl4, libssl3, libxml2, ca-certificates, 
#  libblas3, liblapack3, r-base-core, littler)

# Copy wheels from builder and install RMCP in fresh virtual environment
ENV VENV=/opt/venv
COPY --from=builder /build/wheels/ /tmp/wheels/
ENV PATH="$VENV/bin:$PATH"

# Create fresh virtual environment and install RMCP
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels/ && \
    groupadd -r rmcp && \
    useradd -r -g rmcp -d /app -s /bin/bash rmcp

# Set up application directory
WORKDIR /app
RUN chown rmcp:rmcp /app

# Switch to non-root user
USER rmcp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import rmcp; print('RMCP OK')" || exit 1

# Default to stdio mode for MCP protocol
CMD ["rmcp", "start"]

# Metadata
LABEL org.opencontainers.image.title="RMCP (R Model Context Protocol)"
LABEL org.opencontainers.image.description="Statistical analysis server for AI assistants"
LABEL org.opencontainers.image.vendor="RMCP Project"
LABEL org.opencontainers.image.source="https://github.com/finite-sample/rmcp"