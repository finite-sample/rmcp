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

# Create Python virtual environment with development dependencies
# Use cache mount for pip to dramatically speed up builds
ARG TARGETPLATFORM
ENV VENV=/opt/venv
RUN --mount=type=cache,target=/root/.cache/pip,id=pip-dev-${TARGETPLATFORM} \
    --mount=type=cache,target=/tmp/pip-cache,id=pip-dev-temp-${TARGETPLATFORM} \
    set -eux; \
    python3 -m venv "$VENV"; \
    . "$VENV/bin/activate"; \
    pip install --upgrade pip \
        --cache-dir=/tmp/pip-cache; \
    pip install --cache-dir=/tmp/pip-cache \
        # Development tools (pinned for cache stability)
        "black==23.12.1" \
        "isort==5.13.2" \
        "flake8==6.1.0" \
        "pytest==8.0.0" \
        "pytest-cov==4.0.0" \
        "pytest-asyncio==0.24.0" \
        # Core dependencies
        "click==8.1.7" \
        "jsonschema==4.21.1" \
        "build==1.0.3" \
        # HTTP transport dependencies
        "fastapi==0.109.0" \
        "uvicorn==0.26.0" \
        "sse-starlette==1.8.2" \
        "httpx==0.26.0" \
        # Workflow dependencies
        "pandas==2.2.0" \
        "openpyxl==3.1.2"

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
RUN . "$VENV/bin/activate" && pip install -e .

# Default to bash for development work
CMD ["bash"]

# ============================================================================
# STAGE: Production Builder (Optimized build environment)
# ============================================================================
FROM base AS builder

# Create Python virtual environment with minimal production dependencies
# Use cache mount for pip to dramatically speed up builds
ENV VENV=/opt/venv
RUN --mount=type=cache,target=/root/.cache/pip,id=pip-prod-${TARGETPLATFORM} \
    --mount=type=cache,target=/tmp/pip-cache,id=pip-prod-temp-${TARGETPLATFORM} \
    set -eux; \
    python3 -m venv "$VENV"; \
    . "$VENV/bin/activate"; \
    pip install --upgrade pip \
        --cache-dir=/tmp/pip-cache; \
    pip install --cache-dir=/tmp/pip-cache \
        # Core dependencies (pinned for cache stability)
        "click==8.1.7" \
        "jsonschema==4.21.1" \
        "build==1.0.3" \
        # HTTP transport dependencies
        "fastapi==0.109.0" \
        "uvicorn==0.26.0" \
        "sse-starlette==1.8.2" \
        "httpx==0.26.0" \
        # Workflow dependencies
        "pandas==2.2.0" \
        "openpyxl==3.1.2"

# Copy and build RMCP package
WORKDIR /build
# Copy files in order of change frequency (metadata first, then code)
COPY pyproject.toml ./
# Create minimal README.md for build (excluded by .dockerignore)
RUN echo "# RMCP Production Build" > README.md
COPY rmcp/ ./rmcp/
# Build wheel for production installation with cache mount
RUN --mount=type=cache,target=/root/.cache/pip,id=pip-build-${TARGETPLATFORM} \
    --mount=type=cache,target=/tmp/build-cache,id=build-cache-${TARGETPLATFORM} \
    . "$VENV/bin/activate" && \
    pip wheel --no-deps . -w /build/wheels/ --cache-dir=/tmp/build-cache

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
RUN pip install --no-deps /tmp/wheels/*.whl && \
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