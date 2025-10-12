# Fast CRAN binaries (via r2u) + Python 3.12, multi-arch (amd64/arm64)
FROM rocker/r2u:noble

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps: Python toolchain, occasional build tools, common libs
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        build-essential git \
        libcurl4-openssl-dev libssl-dev libxml2-dev \
        ca-certificates wget; \
    rm -rf /var/lib/apt/lists/*

# (r2u already wires R→APT via bspm; this just makes it explicit/quiet for scripts)
RUN echo "options(bspm.enable=TRUE, bspm.quiet=TRUE)" >> /etc/R/Rprofile.site

# Preinstall your R stack (binary where available ⇒ fast, reproducible)
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

# Python tooling for CI
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      "black>=23.0.0" \
      "isort>=5.12.0" \
      "flake8>=6.0.0" \
      "pytest>=8.0.0" \
      "pytest-asyncio>=0.21.0" \
      "click>=8.1.0" \
      "jsonschema>=4.0.0"

WORKDIR /workspace
ENV PYTHONPATH=/workspace
CMD ["bash"]