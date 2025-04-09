# Use the official Rocker R base image
FROM rocker/r-base:4.2.2

# Install Python 3, pip, and required system dependencies for R packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
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
COPY pyproject.toml .
COPY requirements.txt .
COPY rmcp ./rmcp

# Upgrade pip, install Python dependencies, and install your package
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir .

# Ensure standard output is unbuffered
ENV PYTHONUNBUFFERED=1

# Run the server using the CLI entry point defined in your pyproject.toml,
# which should trigger "rmcp start"
CMD ["rmcp", "start"]
