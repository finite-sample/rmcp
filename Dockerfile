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

# Set up Python environment
WORKDIR /app

# Copy requirements.txt first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY r_econometrics_mcp.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["python", "r_econometrics_mcp.py"]
