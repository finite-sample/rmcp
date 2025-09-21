# CI/CD optimized Docker image for RMCP
# Pre-installs all R packages and Python dependencies for faster CI runs
FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install R and required system dependencies
RUN apt-get update && apt-get install -y \
    r-base \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install all required R packages for RMCP (22 packages)
# This is the time-consuming step that we want to cache
RUN R -e "install.packages(c(\
    'jsonlite', 'plm', 'lmtest', 'sandwich', 'AER', 'dplyr', \
    'forecast', 'vars', 'urca', 'tseries', 'nortest', 'car', \
    'rpart', 'randomForest', 'ggplot2', 'gridExtra', 'tidyr', \
    'rlang', 'readxl', 'base64enc', 'reshape2'\
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