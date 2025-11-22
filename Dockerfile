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

# Install uv and create virtual environment with development dependencies
ARG TARGETPLATFORM
ENV VENV=/opt/venv
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-dev-${TARGETPLATFORM} \
    set -eux; \
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh; \
    . /root/.cargo/env; \
    uv venv "$VENV"; \
    . "$VENV/bin/activate"; \
    uv pip install \
        # Development tools
        "ruff>=0.4.0" \
        "pytest>=8.2.0" \
        "pytest-cov>=4.0.0" \
        "pytest-asyncio>=0.21.0" \
        # Core dependencies
        "click>=8.1.0" \
        "jsonschema>=4.0.0" \
        # HTTP transport dependencies
        "fastapi>=0.100.0" \
        "uvicorn>=0.20.0" \
        "sse-starlette>=1.6.0" \
        "httpx>=0.25.0" \
        # Workflow dependencies
        "pandas>=1.5.0" \
        "openpyxl>=3.0.0"

# Add uv to PATH
ENV PATH="/root/.cargo/bin:$PATH"

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

# Install RMCP in development mode
RUN . "$VENV/bin/activate" && \
    . /root/.cargo/env && \
    uv pip install -e .

# Default to bash for development work
CMD ["bash"]

# ============================================================================
# STAGE: Production Builder (Optimized build environment)
# ============================================================================
FROM base AS builder

# Install uv and create Python virtual environment with minimal production dependencies
ENV VENV=/opt/venv
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-prod-${TARGETPLATFORM} \
    set -eux; \
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh; \
    . /root/.cargo/env; \
    uv venv "$VENV"; \
    . "$VENV/bin/activate"; \
    uv pip install \
        # Core dependencies
        "click>=8.1.0" \
        "jsonschema>=4.0.0" \
        # HTTP transport dependencies
        "fastapi>=0.100.0" \
        "uvicorn>=0.20.0" \
        "sse-starlette>=1.6.0" \
        "httpx>=0.25.0" \
        # Workflow dependencies
        "pandas>=1.5.0" \
        "openpyxl>=3.0.0"

# Add uv to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Copy and build RMCP package
WORKDIR /build
# Copy files in order of change frequency (metadata first, then code)
COPY pyproject.toml ./
# Create minimal README.md for build (excluded by .dockerignore)
RUN echo "# RMCP Production Build" > README.md
COPY rmcp/ ./rmcp/
# Build wheel for production installation with uv
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-build-${TARGETPLATFORM} \
    . "$VENV/bin/activate" && \
    . /root/.cargo/env && \
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
FROM ubuntu:noble AS production

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install only runtime dependencies (no build tools)
# Use cache mount for apt downloads only (avoid lock conflicts)
RUN --mount=type=cache,target=/var/cache/apt,id=apt-prod-${TARGETPLATFORM} \
    set -eux; \
    # Clean any existing locks and ensure clean state
    rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock*; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        # Python runtime (no dev packages)
        python3 python3-venv \
        # Runtime libraries for compiled packages
        libcurl4 libssl3 libxml2 \
        # Essential utilities
        ca-certificates \
        # Runtime math libraries
        libblas3 liblapack3 \
        # R runtime dependencies
        r-base-core \
        littler; \
    # Clean package lists and temporary files
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

# Copy R packages and configuration from production-base, then configure
COPY --from=production-base /usr/local/lib/R /usr/local/lib/R
COPY --from=production-base /usr/lib/R /usr/lib/R  
COPY --from=production-base /etc/R /etc/R
RUN echo "options(bspm.sudo = TRUE)" >> /etc/R/Rprofile.site

# Copy Python virtual environment and install RMCP (merged operations)
ENV VENV=/opt/venv
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/wheels/ /tmp/wheels/
ENV PATH="$VENV/bin:$PATH"

# Install RMCP, create user, and setup directory in single layer  
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    . /root/.cargo/env && \
    uv pip install --system --no-deps /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels/ /root/.cargo && \
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