# Use a lightweight Python base image
FROM python:3.10-slim

# Install R and required system dependencies
RUN apt-get update && apt-get install -y \
    r-base \
    r-base-dev \
    libxml2-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install required R packages
RUN R -e "install.packages(c('plm', 'lmtest', 'sandwich', 'AER', 'jsonlite'), repos='https://cloud.r-project.org/')"

# Set up the working directory
WORKDIR /app

# Copy package management files and source code
# (Assumes you have a requirements.txt file for additional Python dependencies.)
COPY pyproject.toml .
COPY requirements.txt .
COPY rmcp ./rmcp

# Install Python dependencies and then install your package using pyproject.toml configuration
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir .

# Ensure standard output is unbuffered
ENV PYTHONUNBUFFERED=1

# Run the server using the CLI entry point defined in your pyproject.toml;
# this should trigger "rmcp start"
CMD ["rmcp", "start"]
