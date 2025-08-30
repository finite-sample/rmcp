# Use lightweight Python base with R
FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install minimal R and only essential system dependencies
RUN apt-get update && apt-get install -y \
    r-base \
    libcurl4-openssl-dev \
    libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install essential R packages to avoid CI/CD timeouts
RUN R -e "install.packages(c('jsonlite', 'dplyr', 'tseries'), repos='https://cloud.r-project.org/', quiet=TRUE)"

# Set the working directory
WORKDIR /app

# Copy the project files to the container.
# (Assumes your package files and pyproject.toml are in the repository root)
COPY pyproject.toml .
COPY requirements.txt .
COPY src/rmcp ./src/rmcp

# Upgrade pip, install Python dependencies from requirements.txt, 
# and then install your package using pyproject.toml configuration.
# We add --break-system-packages to avoid PEP 668 issues.
RUN pip3 install --upgrade pip --break-system-packages && \
    pip3 install --no-cache-dir -r requirements.txt --break-system-packages && \
    pip3 install --no-cache-dir . --break-system-packages

# Ensure stdout is unbuffered.
ENV PYTHONUNBUFFERED=1

# Run the server using the CLI entry point defined in your pyproject.toml
CMD ["rmcp", "start"]
