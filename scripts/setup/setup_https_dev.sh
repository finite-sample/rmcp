#!/bin/bash
# Setup HTTPS development environment with mkcert
# Creates local CA and SSL certificates for RMCP development

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CERTS_DIR="$PROJECT_ROOT/certs"

echo -e "${BLUE}🔐 Setting up HTTPS development environment for RMCP${NC}"
echo "=================================================================="

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if mkcert is installed
if ! command -v mkcert &> /dev/null; then
    echo -e "${YELLOW}📦 mkcert not found. Installing...${NC}"

    # Detect OS and install mkcert
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install mkcert
        else
            print_error "Homebrew not found. Please install mkcert manually:"
            print_error "https://github.com/FiloSottile/mkcert#installation"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            sudo apt-get update
            sudo apt-get install -y libnss3-tools
            # Download latest mkcert
            MKCERT_VERSION=$(curl -s https://api.github.com/repos/FiloSottile/mkcert/releases/latest | grep "tag_name" | cut -d '"' -f 4)
            curl -Lo mkcert "https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-${MKCERT_VERSION}-linux-amd64"
            chmod +x mkcert
            sudo mv mkcert /usr/local/bin/
        elif command -v yum &> /dev/null; then
            # RHEL/CentOS/Fedora
            sudo yum install -y nss-tools
            # Download latest mkcert
            MKCERT_VERSION=$(curl -s https://api.github.com/repos/FiloSottile/mkcert/releases/latest | grep "tag_name" | cut -d '"' -f 4)
            curl -Lo mkcert "https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-${MKCERT_VERSION}-linux-amd64"
            chmod +x mkcert
            sudo mv mkcert /usr/local/bin/
        else
            print_error "Unsupported Linux distribution. Please install mkcert manually:"
            print_error "https://github.com/FiloSottile/mkcert#installation"
            exit 1
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows (Git Bash/WSL)
        print_error "Windows detected. Please install mkcert manually:"
        print_error "https://github.com/FiloSottile/mkcert#windows"
        exit 1
    else
        print_error "Unsupported OS: $OSTYPE"
        print_error "Please install mkcert manually: https://github.com/FiloSottile/mkcert#installation"
        exit 1
    fi
else
    print_status "mkcert is already installed"
fi

# Verify mkcert installation
if ! command -v mkcert &> /dev/null; then
    print_error "mkcert installation failed"
    exit 1
fi

# Create certificates directory
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

# Install local CA (if not already installed)
echo -e "${BLUE}🏢 Setting up local Certificate Authority...${NC}"
if mkcert -install; then
    print_status "Local CA installed successfully"
else
    print_warning "Local CA may already be installed"
fi

# Generate certificates for various localhost variations
echo -e "${BLUE}📜 Generating SSL certificates...${NC}"

# Remove existing certificates
rm -f localhost*.pem *.key *.crt

# Generate certificate for localhost, 127.0.0.1, ::1, and custom domains
DOMAINS=(
    "localhost"
    "127.0.0.1"
    "::1"
    "rmcp.local"
    "*.rmcp.local"
    "rmcp-dev.local"
    "rmcp-test.local"
)

# Join domains with spaces
DOMAIN_LIST=$(IFS=' '; echo "${DOMAINS[*]}")

echo "Generating certificate for domains: $DOMAIN_LIST"
mkcert $DOMAIN_LIST

# Rename the generated files to standard names
mv *localhost*.pem localhost.pem 2>/dev/null || true
mv *localhost*-key.pem localhost-key.pem 2>/dev/null || true

# If the rename didn't work, find the actual filenames
if [[ ! -f "localhost.pem" ]]; then
    CERT_FILE=$(find . -name "*+*.pem" -not -name "*key.pem" | head -1)
    KEY_FILE=$(find . -name "*key.pem" | head -1)

    if [[ -n "$CERT_FILE" ]] && [[ -n "$KEY_FILE" ]]; then
        mv "$CERT_FILE" localhost.pem
        mv "$KEY_FILE" localhost-key.pem
        print_status "Renamed certificates to standard names"
    fi
fi

# Verify certificates were created
if [[ -f "localhost.pem" ]] && [[ -f "localhost-key.pem" ]]; then
    print_status "SSL certificates generated successfully"

    # Show certificate info
    echo -e "${BLUE}📋 Certificate Information:${NC}"
    echo "  Certificate: $CERTS_DIR/localhost.pem"
    echo "  Private Key: $CERTS_DIR/localhost-key.pem"
    echo "  Valid for domains: $DOMAIN_LIST"

    # Show certificate details
    echo -e "${BLUE}🔍 Certificate Details:${NC}"
    openssl x509 -in localhost.pem -text -noout | grep -A 1 "Subject:"
    openssl x509 -in localhost.pem -text -noout | grep -A 5 "Subject Alternative Name"

    # Show expiration date
    EXPIRY=$(openssl x509 -in localhost.pem -noout -enddate | cut -d= -f2)
    echo "  Expires: $EXPIRY"

else
    print_error "Failed to generate SSL certificates"
    exit 1
fi

# Create a simple configuration file for RMCP
cat > "$CERTS_DIR/https-config.json" << EOF
{
  "http": {
    "host": "localhost",
    "port": 8443,
    "ssl_keyfile": "$CERTS_DIR/localhost-key.pem",
    "ssl_certfile": "$CERTS_DIR/localhost.pem",
    "cors_origins": [
      "https://localhost:*",
      "https://127.0.0.1:*",
      "https://rmcp.local:*",
      "https://*.rmcp.local:*"
    ]
  },
  "logging": {
    "level": "INFO"
  }
}
EOF

print_status "Created HTTPS configuration file: $CERTS_DIR/https-config.json"

# Create environment file for easy sourcing
cat > "$CERTS_DIR/https-env.sh" << EOF
#!/bin/bash
# HTTPS development environment variables
export RMCP_HTTP_HOST="localhost"
export RMCP_HTTP_PORT="8443"
export RMCP_SSL_KEYFILE="$CERTS_DIR/localhost-key.pem"
export RMCP_SSL_CERTFILE="$CERTS_DIR/localhost.pem"
export RMCP_LOG_LEVEL="DEBUG"

echo "🔒 HTTPS environment configured:"
echo "  Host: \$RMCP_HTTP_HOST"
echo "  Port: \$RMCP_HTTP_PORT"
echo "  Key:  \$RMCP_SSL_KEYFILE"
echo "  Cert: \$RMCP_SSL_CERTFILE"
EOF

chmod +x "$CERTS_DIR/https-env.sh"
print_status "Created environment script: $CERTS_DIR/https-env.sh"

# Create Docker environment file
cat > "$CERTS_DIR/.env.docker" << EOF
# Docker HTTPS environment
RMCP_HTTP_HOST=0.0.0.0
RMCP_HTTP_PORT=8443
RMCP_SSL_KEYFILE=/app/certs/localhost-key.pem
RMCP_SSL_CERTFILE=/app/certs/localhost.pem
RMCP_LOG_LEVEL=DEBUG
EOF

print_status "Created Docker environment file: $CERTS_DIR/.env.docker"

# Add certificates to .gitignore if not already there
GITIGNORE="$PROJECT_ROOT/.gitignore"
if [[ ! -f "$GITIGNORE" ]] || ! grep -q "certs/" "$GITIGNORE"; then
    echo -e "\n# HTTPS development certificates" >> "$GITIGNORE"
    echo "certs/" >> "$GITIGNORE"
    print_status "Added certs/ to .gitignore"
fi

echo -e "${GREEN}🎉 HTTPS development environment setup complete!${NC}"
echo
echo -e "${BLUE}🚀 Quick Start:${NC}"
echo "  1. Start RMCP with HTTPS:"
echo "     source $CERTS_DIR/https-env.sh"
echo "     rmcp serve-http"
echo
echo "  2. Or use the config file:"
echo "     rmcp serve-http --config $CERTS_DIR/https-config.json"
echo
echo "  3. Test the HTTPS endpoint:"
echo "     curl -k https://localhost:8443/health"
echo
echo -e "${BLUE}📝 Next Steps:${NC}"
echo "  • Run 'docker-compose up' to test in Docker"
echo "  • Check out the integration tests in tests/integration/transport/"
echo "  • Add custom domains to /etc/hosts if needed:"
echo "    127.0.0.1 rmcp.local rmcp-dev.local"
echo
print_status "Setup complete! 🔐"
