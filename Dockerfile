FROM rocker/r2u:noble AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

LABEL org.opencontainers.image.title="RMCP Runtime Base"
LABEL org.opencontainers.image.description="R runtime and statistical packages for RMCP"
LABEL org.opencontainers.image.vendor="RMCP Project"
LABEL org.opencontainers.image.source="https://github.com/finite-sample/rmcp"

ARG TARGETPLATFORM
RUN --mount=type=cache,target=/var/cache/apt,id=apt-runtime-${TARGETPLATFORM} \
    set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        libcurl4 \
        libssl3 \
        libxml2 \
        libblas3 \
        liblapack3 \
        libgfortran5 \
        ca-certificates; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN echo "options(bspm.enable=TRUE, bspm.quiet=TRUE)" >> /etc/R/Rprofile.site

RUN --mount=type=cache,target=/tmp/downloaded_packages,id=r-runtime-${TARGETPLATFORM} \
    R -q -e "packages <- c( \
      'jsonlite', 'dplyr', 'rlang', \
      'plm', 'lmtest', 'sandwich', 'AER', 'car', 'broom', \
      'forecast', 'vars', 'urca', 'tseries', \
      'cluster', 'rpart', 'randomForest', \
      'ggplot2', 'gridExtra', \
      'readxl', 'openxlsx', 'base64enc', 'reshape2', 'knitr', 'nortest' \
    ); install.packages(packages, Ncpus = parallel::detectCores()); missing <- setdiff(packages, rownames(installed.packages())); if (length(missing)) stop('Failed to install: ', paste(missing, collapse = ', '))"

RUN R -q -e " \
library(jsonlite); \
library(dplyr); \
library(ggplot2); \
library(forecast); \
library(randomForest); \
cat('R version:', R.version.string, '\\n'); \
cat('Installed packages:', length(.packages(all.available=TRUE)), '\\n'); \
"

RUN set -eux; \
    BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ); \
    R -q -e "jsonlite::write_json( \
      list(build_date = '${BUILD_DATE}', r_version = R.version.string, base_image = 'rocker/r2u:noble'), \
      '/opt/rmcp-base-info.json', auto_unbox = TRUE, pretty = TRUE \
    )"; \
    rm -rf /tmp/* /var/tmp/* /root/.cache

WORKDIR /workspace

FROM base AS development

ARG TARGETPLATFORM
RUN --mount=type=cache,target=/var/cache/apt,id=apt-development-${TARGETPLATFORM} \
    set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        python3-dev \
        libcurl4-openssl-dev \
        libssl-dev \
        libxml2-dev \
        libuv1-dev \
        pkg-config \
        libblas-dev \
        liblapack-dev \
        gfortran \
        libnss3-tools \
        curl; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${TARGETPLATFORM}" in \
        "linux/amd64") MKCERT_ARCH="linux-amd64" ;; \
        "linux/arm64") MKCERT_ARCH="linux-arm64" ;; \
        *) echo "Unsupported platform: ${TARGETPLATFORM}"; exit 1 ;; \
    esac; \
    curl -Lo /usr/local/bin/mkcert \
        "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-${MKCERT_ARCH}"; \
    chmod +x /usr/local/bin/mkcert; \
    mkcert -version

RUN R -q -e "packages <- c('styler', 'lintr', 'testthat'); install.packages(packages, Ncpus = parallel::detectCores()); missing <- setdiff(packages, rownames(installed.packages())); if (length(missing)) stop('Failed to install: ', paste(missing, collapse = ', '))"

COPY --from=ghcr.io/astral-sh/uv:0.12.0 /uv /uvx /bin/

WORKDIR /workspace
ENV PYTHONPATH=/workspace \
    VIRTUAL_ENV=/workspace/.venv \
    PATH="/workspace/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN echo "# RMCP Development Environment" > README.md
COPY rmcp/ ./rmcp/

RUN --mount=type=cache,target=/root/.cache/uv,id=uv-development-${TARGETPLATFORM} \
    uv sync --frozen --group dev --all-extras --reinstall-package rmcp && \
    python -c "import rmcp; print('RMCP installed successfully')"

CMD ["bash"]

FROM base AS builder

ARG TARGETPLATFORM
COPY --from=ghcr.io/astral-sh/uv:0.12.0 /uv /uvx /bin/

WORKDIR /build
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN echo "# RMCP Production Build" > README.md
COPY rmcp/ ./rmcp/

RUN --mount=type=cache,target=/root/.cache/uv,id=uv-production-${TARGETPLATFORM} \
    uv sync --frozen --no-dev --no-editable --reinstall-package rmcp && \
    /opt/venv/bin/python -c "import rmcp; print('RMCP installed successfully')"

FROM base AS production

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

RUN groupadd -r rmcp && \
    useradd -r -g rmcp -d /app -s /bin/bash rmcp && \
    mkdir -p /app && \
    chown rmcp:rmcp /app

WORKDIR /app
USER rmcp

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import rmcp; print('RMCP OK')" || exit 1

CMD ["rmcp", "start"]

LABEL org.opencontainers.image.title="RMCP (R Model Context Protocol)"
LABEL org.opencontainers.image.description="Statistical analysis server for AI assistants"
LABEL org.opencontainers.image.vendor="RMCP Project"
LABEL org.opencontainers.image.source="https://github.com/finite-sample/rmcp"
