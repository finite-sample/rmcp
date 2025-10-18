# Multi-Target Dockerfile for RMCP
# Supports both development and production environments
#
# Usage:
#   Development: docker build --target development -t rmcp:dev .
#   Production:  docker build --target production -t rmcp:prod .

# ============================================================================
# STAGE: Base Environment (Shared R and system dependencies)
# ============================================================================
FROM rocker/r2u:noble AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (shared between dev and prod)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        build-essential git \
        libcurl4-openssl-dev libssl-dev libxml2-dev \
        ca-certificates wget \
        # Additional build dependencies
        pkg-config \
        gcc g++ \
        libblas-dev liblapack-dev \
        gfortran; \
    rm -rf /var/lib/apt/lists/*

# Make r2u behavior explicit for scripts
RUN echo "options(bspm.enable=TRUE, bspm.quiet=TRUE)" >> /etc/R/Rprofile.site

# Install core R packages (shared between dev and prod)
RUN R -q -e "install.packages(c( \
  'jsonlite','plm','lmtest','sandwich','AER','dplyr', \
  'forecast','vars','urca','tseries','nortest','car', \
  'rpart','randomForest','ggplot2','gridExtra','tidyr', \
  'rlang','readxl','openxlsx','base64enc','reshape2','knitr','broom', \
  'MASS','boot','survival','nlme','mgcv','lme4','glmnet', \
  'e1071','caret','nnet','gbm','xgboost','kernlab','cluster', \
  'zoo','xts','TTR','quantmod','data.table','lattice', \
  'corrplot','viridis','RColorBrewer','lavaan' \
))"

# ============================================================================
# STAGE: Development Environment (Full development stack)
# ============================================================================
FROM base AS development

# Install additional R packages for development
RUN R -q -e "install.packages(c('styler','lintr','testthat'))"

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
# STAGE: Production Runtime (Minimal production environment)
# ============================================================================
FROM rocker/r2u:noble AS production

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
        libblas3 liblapack3; \
    # Clean up aggressively
    rm -rf /var/lib/apt/lists/* \
           /tmp/* \
           /var/tmp/* \
           /root/.cache

# Copy R packages from base stage
COPY --from=base /usr/local/lib/R/site-library /usr/local/lib/R/site-library
COPY --from=base /etc/R/Rprofile.site /etc/R/Rprofile.site

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