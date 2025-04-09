# Use the official Rocker R base image (with a recent R version)
FROM rocker/r-base:4.2.2

# Install Python3, pip and required system dependencies for R packages.
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libxml2-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install required R packages.
RUN R -e "install.packages(c('plm', 'lmtest', 'sandwich', 'AER', 'jsonlite'), repos='https://cloud.r-project.org/')"

# Set the working directory
WORKDIR /app

# Copy the project files to the container.
# (Assumes your package files and pyproject.toml are in the repository root)
COPY pyproject.toml .
COPY requirements.txt .
COPY rmcp ./rmcp

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
