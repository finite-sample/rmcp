FROM rocker/r2u:noble

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps (Python + build tools + common libs)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        build-essential git \
        libcurl4-openssl-dev libssl-dev libxml2-dev \
        ca-certificates wget; \
    rm -rf /var/lib/apt/lists/*

# Make r2u behavior explicit for scripts
RUN echo "options(bspm.enable=TRUE, bspm.quiet=TRUE)" >> /etc/R/Rprofile.site

# Preinstall R stack (binaries via r2u/bspm => fast)
RUN R -q -e "install.packages(c( \
  'jsonlite','plm','lmtest','sandwich','AER','dplyr', \
  'forecast','vars','urca','tseries','nortest','car', \
  'rpart','randomForest','ggplot2','gridExtra','tidyr', \
  'rlang','readxl','openxlsx','base64enc','reshape2','knitr','broom', \
  'MASS','boot','survival','nlme','mgcv','lme4','glmnet', \
  'e1071','caret','nnet','gbm','xgboost','kernlab','cluster', \
  'zoo','xts','TTR','quantmod','data.table','lattice', \
  'corrplot','viridis','RColorBrewer','lavaan', \
  'styler','lintr','testthat' \
))"

# ---- Python: create a venv to avoid PEP 668 issues ----
ENV VENV=/opt/venv
RUN set -eux; \
    python3 -m venv "$VENV"; \
    . "$VENV/bin/activate"; \
    pip install --upgrade pip; \
    pip install --no-cache-dir \
        "black>=23.0.0" \
        "isort>=5.12.0" \
        "flake8>=6.0.0" \
        "pytest>=8.0.0" \
        "pytest-cov>=4.0.0" \
        "pytest-asyncio>=0.21.0" \
        "click>=8.1.0" \
        "jsonschema>=4.0.0" \
        "build>=0.10.0" \
        "pandas>=1.5.0" \
        "openpyxl>=3.0.0"

# Ensure venv tools are first on PATH for subsequent steps/CI
ENV PATH="$VENV/bin:$PATH"

WORKDIR /workspace
ENV PYTHONPATH=/workspace

CMD ["bash"]
