# CI/CD optimized Docker image for RMCP
# Pre-installs all R packages and Python dependencies for faster CI runs
FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install R 4.4+ and required system dependencies
RUN apt-get update && apt-get install -y \
    gnupg2 \
    wget \
    ca-certificates \
    && wget -qO- https://cloud.r-project.org/bin/linux/debian/marutter_pubkey.asc | \
       tee /etc/apt/trusted.gpg.d/cran_debian_key.asc \
    && echo "deb https://cloud.r-project.org/bin/linux/debian bookworm-cran40/" >> /etc/apt/sources.list \
    && apt-get update && apt-get install -y \
    r-base \
    r-base-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install all required R packages for RMCP (45+ packages)
# This is the time-consuming step that we want to cache
# Includes core structured tools + commonly used flexible_r packages
RUN R -e "install.packages(c(\
    # Core structured tools packages \
    'jsonlite', 'plm', 'lmtest', 'sandwich', 'AER', 'dplyr', \
    'forecast', 'vars', 'urca', 'tseries', 'nortest', 'car', \
    'rpart', 'randomForest', 'ggplot2', 'gridExtra', 'tidyr', \
    'rlang', 'readxl', 'openxlsx', 'base64enc', 'reshape2', 'knitr', 'broom', \
    # Common flexible_r packages for advanced statistics \
    'MASS', 'boot', 'survival', 'nlme', 'mgcv', 'lme4', 'glmnet', \
    'e1071', 'caret', 'nnet', 'gbm', 'xgboost', 'kernlab', 'cluster', \
    'zoo', 'xts', 'TTR', 'quantmod', 'data.table', 'lattice', \
    'corrplot', 'viridis', 'RColorBrewer', 'lavaan'\
    ), repos='https://cran.rstudio.com/', quiet=TRUE)"

# Install Python dependencies needed for CI
RUN pip install --no-cache-dir \
    black>=23.0.0 \
    isort>=5.12.0 \
    flake8>=6.0.0 \
    pytest>=8.0.0 \
    pytest-asyncio>=0.21.0 \
    click>=8.1.0 \
    jsonschema>=4.0.0

# Set working directory for CI
WORKDIR /workspace

# Ensure stdout is unbuffered for CI logs
ENV PYTHONUNBUFFERED=1

# Set Python path to workspace for package installation
ENV PYTHONPATH=/workspace

# Default command for CI (will be overridden in workflows)
CMD ["bash"]