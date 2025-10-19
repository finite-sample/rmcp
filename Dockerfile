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
ENV VENV=/opt/venv
RUN set -eux; \
    python3 -m venv "$VENV"; \
    . "$VENV/bin/activate"; \
    pip install --upgrade pip; \
    pip install --no-cache-dir \
        # Development tools
        "black>=23.0.0" \
        "isort>=5.12.0" \
        "flake8>=6.0.0" \
        "pytest>=8.0.0" \
        "pytest-cov>=4.0.0" \
        "pytest-asyncio>=0.21.0" \
        # Core dependencies
        "click>=8.1.0" \
        "jsonschema>=4.0.0" \
        "build>=0.10.0" \
        # Optional HTTP transport dependencies
        "fastapi>=0.100.0" \
        "uvicorn>=0.20.0" \
        "sse-starlette>=1.6.0" \
        "httpx>=0.24.0" \
        # Workflow dependencies
        "pandas>=1.5.0" \
        "openpyxl>=3.0.0"

# Ensure venv tools are first on PATH for subsequent steps/CI
ENV PATH="$VENV/bin:$PATH"

# Development workspace setup
WORKDIR /workspace
ENV PYTHONPATH=/workspace

# Default to bash for development work
CMD ["bash"]

# ============================================================================
# STAGE: Production Builder (Optimized build environment)
# ============================================================================
FROM base AS builder

# Create Python virtual environment with minimal production dependencies
ENV VENV=/opt/venv
RUN set -eux; \
    python3 -m venv "$VENV"; \
    . "$VENV/bin/activate"; \
    pip install --upgrade pip; \
    pip install --no-cache-dir \
        # Core dependencies
        "click>=8.1.0" \
        "jsonschema>=4.0.0" \
        "build>=0.10.0" \
        # HTTP transport dependencies
        "fastapi>=0.100.0" \
        "uvicorn>=0.20.0" \
        "sse-starlette>=1.6.0" \
        "httpx>=0.24.0" \
        # Workflow dependencies
        "pandas>=1.5.0" \
        "openpyxl>=3.0.0"

# Copy and build RMCP package
WORKDIR /build
COPY pyproject.toml ./
COPY rmcp/ ./rmcp/
# Create minimal README.md for build (excluded by .dockerignore)
RUN echo "# RMCP Production Build" > README.md
# Build wheel for production installation
RUN . "$VENV/bin/activate" && pip wheel --no-deps . -w /build/wheels/

# ============================================================================
# STAGE: Production Runtime (Optimized from base image)
# ============================================================================
FROM base AS production-base

# Remove development tools to minimize size
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
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

# ============================================================================
# STAGE: Production Runtime (Final minimal environment)
# ============================================================================
FROM ubuntu:noble AS production

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install only runtime dependencies (no build tools)
RUN set -eux; \
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
    # Clean up aggressively
    rm -rf /var/lib/apt/lists/* \
           /tmp/* \
           /var/tmp/* \
           /root/.cache

# Copy R packages and configuration from production-base
COPY --from=production-base /usr/local/lib/R /usr/local/lib/R
COPY --from=production-base /usr/lib/R /usr/lib/R  
COPY --from=production-base /etc/R /etc/R

# Configure R for container environment
RUN echo "options(bspm.sudo = TRUE)" >> /etc/R/Rprofile.site

# Copy Python virtual environment from builder stage
ENV VENV=/opt/venv
COPY --from=builder /opt/venv /opt/venv

# Copy the built wheel from builder stage  
COPY --from=builder /build/wheels/ /tmp/wheels/

# Ensure venv tools are first on PATH
ENV PATH="$VENV/bin:$PATH"

# Install RMCP from pre-built wheel (as root before user switch)
RUN pip install --no-deps /tmp/wheels/*.whl

# Clean up wheels
RUN rm -rf /tmp/wheels/

# Create non-root user for security
RUN groupadd -r rmcp && useradd -r -g rmcp -d /app -s /bin/bash rmcp

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