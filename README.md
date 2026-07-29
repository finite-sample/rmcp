# RMCP: Statistical Analysis through Natural Conversation

[![Python application](https://github.com/finite-sample/rmcp/actions/workflows/ci.yml/badge.svg)](https://github.com/finite-sample/rmcp/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/rmcp.svg)](https://pypi.org/project/rmcp/)
[![Downloads](https://pepy.tech/badge/rmcp)](https://pepy.tech/project/rmcp)
[![Documentation](https://github.com/finite-sample/rmcp/actions/workflows/docs.yml/badge.svg)](https://finite-sample.github.io/rmcp/)
[![License](https://img.shields.io/github/license/finite-sample/rmcp)](https://github.com/finite-sample/rmcp/blob/main/LICENSE)

**Turn conversations into comprehensive statistical analysis** - A Model Context Protocol (MCP) server with **54 tools** across 11 categories and **429 R packages** from systematic CRAN task views. RMCP enables AI assistants to perform sophisticated statistical modeling, econometric analysis, machine learning, time series analysis, and data science tasks through natural conversation.

## 🚀 Quick Start (30 seconds)

### 🌐 **Try the Live Server** (No Installation Required)

**MCP Endpoint**: `https://rmcp-server-394229601724.us-central1.run.app/mcp` (bearer token required)
**Health Check**: `https://rmcp-server-394229601724.us-central1.run.app/health`

### 🖥️ **Or Install Locally**

```bash
pip install rmcp
rmcp start
```

That's it! RMCP is now ready to handle statistical analysis requests via Claude Desktop, Claude web, or any MCP client.

**🎯 [Working examples →](examples/quick_start_guide.md)** | **🔧 [Troubleshooting →](#-quick-troubleshooting)**

## ✨ What Can RMCP Do?

### 📊 **Regression & Economics**
Linear regression, logistic models, panel data, instrumental variables → *"Analyze ROI of marketing spend"*

### ⏰ **Time Series & Forecasting**
ARIMA models, decomposition, stationarity testing → *"Forecast next quarter's sales"*

### 🧠 **Machine Learning**
Clustering, decision trees, random forests → *"Segment customers by behavior"*

### 📈 **Statistical Testing**
T-tests, ANOVA, chi-square, normality tests → *"Is my A/B test significant?"*

### 📋 **Data Analysis**
Descriptive stats, outlier detection, correlation analysis → *"Summarize this dataset"*

### 🔄 **Data Transformation**
Standardization, winsorization, lag/lead variables → *"Prepare data for modeling"*

### 📊 **Professional Visualizations**
Inline plots in Claude: scatter plots, histograms, heatmaps → *"Show me a correlation matrix"*

### 📁 **Smart File Operations**
CSV, Excel, JSON import with validation → *"Load and analyze my sales data"*

### 🤖 **Natural Language Features**
Formula building, error recovery, example datasets → *"Help me build a regression formula"*

**👉 [See working examples →](examples/quick_start_guide.md)**

## 📊 Real Usage with Claude

### Business Analysis
**You:** *"I have sales data and marketing spend. Can you analyze the ROI?"*

**Claude:** *"I'll run a regression analysis to measure marketing effectiveness..."*

**Result:** *"Every $1 spent on marketing generates $4.70 in sales. The relationship is highly significant (p < 0.001) with R² = 0.979"*

### Economic Research
**You:** *"Test if GDP growth and unemployment follow Okun's Law using my country data"*

**Claude:** *"I'll analyze the correlation between GDP growth and unemployment..."*

**Result:** *"Strong support for Okun's Law: correlation r = -0.944. Higher GDP growth significantly reduces unemployment."*

### Customer Analytics
**You:** *"Predict customer churn using tenure and monthly charges"*

**Claude:** *"I'll build a logistic regression model for churn prediction..."*

**Result:** *"Model achieves 100% accuracy. Each additional month of tenure reduces churn risk by 11.3%. Higher charges increase churn risk by 3% per dollar."*

## 📦 Installation

### Prerequisites
- **Python 3.11+**
- **R 4.4.0+** with **comprehensive package ecosystem**: RMCP uses a systematic 429-package whitelist from CRAN task views organized into 19+ categories:

```r
# Core packages (install these first)
install.packages(c(
  "jsonlite", "dplyr", "ggplot2", "broom", "plm", "forecast",
  "randomForest", "rpart", "caret", "AER", "vars", "mgcv"
))

# Full ecosystem automatically available: Machine Learning (61 packages),
# Econometrics (55 packages), Time Series (57 packages),
# Bayesian Analysis (40 packages), and more
```

**Package Selection**: Evidence-based, using CRAN task views and download statistics

### Install RMCP

```bash
# Standard installation
pip install rmcp

# The Streamable HTTP transport ships in the base install.
# This extra adds pandas/openpyxl for Excel data handling.
pip install rmcp[http]

# Development installation
git clone https://github.com/finite-sample/rmcp.git
cd rmcp
pip install -e ".[dev]"
```

### Claude Desktop Integration

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "rmcp": {
      "command": "rmcp",
      "args": ["start"]
    }
  }
}
```

### HTTP Server Integration (Claude Web)

RMCP serves the MCP **Streamable HTTP** transport at `/mcp` (spec 2025-11-25),
compatible with Claude custom connectors and OpenAI's Responses API / ChatGPT
remote MCP support. Remote deployments require a bearer token.

**Production Server**:
```
Server URL: https://rmcp-server-394229601724.us-central1.run.app/mcp
```

**Test the connection**:
```bash
# Health check
curl https://rmcp-server-394229601724.us-central1.run.app/health

# Initialize MCP session (Streamable HTTP)
curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $RMCP_API_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0"}}}'
```

**Local HTTP server**:
```bash
# Localhost (no auth required)
rmcp serve-http

# Remote bind requires a bearer token (or --allow-unauthenticated)
RMCP_API_KEY=your-secret rmcp serve-http --host 0.0.0.0 --port 8080
```

### Command Line Usage

```bash
# Start MCP server (for Claude Desktop)
rmcp start

# Start HTTP server (for web apps)
rmcp serve-http --host 0.0.0.0 --port 8080

# Start HTTPS server (production ready)
rmcp serve-http --ssl-keyfile server.key --ssl-certfile server.crt --port 8443

# Quick HTTPS setup for development
./scripts/setup/setup_https_dev.sh && source certs/https-env.sh && rmcp serve-http

# Use configuration file
rmcp --config ~/.rmcp/config.json start

# Enable debug mode
rmcp --debug start

# Check installation
rmcp --version
```

### Shell Completion

```bash
# zsh — add to ~/.zshrc
eval "$(_RMCP_COMPLETE=zsh_source rmcp)"

# bash — add to ~/.bashrc (requires bash 4.4+)
eval "$(_RMCP_COMPLETE=bash_source rmcp)"

# fish — write to the completions directory
_RMCP_COMPLETE=fish_source rmcp > ~/.config/fish/completions/rmcp.fish
```

macOS ships bash 3.2, which is too old — click prints a warning and completion
does nothing. Use zsh (the macOS default) or install a newer bash.

### ⚙️ Configuration

RMCP supports flexible configuration through environment variables, configuration files, and command-line options:

```bash
# Environment variables
export RMCP_HTTP_PORT=9000
export RMCP_R_TIMEOUT=180
export RMCP_LOG_LEVEL=DEBUG
rmcp start

# Configuration file (~/.rmcp/config.json)
{
  "http": {"port": 9000},
  "r": {"timeout": 180},
  "logging": {"level": "DEBUG"}
}

# Docker with environment variables
docker run -e RMCP_HTTP_HOST=0.0.0.0 -e RMCP_HTTP_PORT=8000 rmcp:latest
```

**📖 [Complete Configuration Guide →](docs/configuration/index.rst)** (auto-generated from code)

## 🔥 Key Features

- **🎯 Natural Conversation**: Ask questions in plain English, get statistical analysis
- **📚 Comprehensive Package Ecosystem**: 429 R packages from systematic CRAN task views
- **📊 Professional Output**: Formatted results with markdown tables and inline visualizations
- **🔒 Production Ready**: Official MCP SDK with stdio and Streamable HTTP transports, plus bearer-token auth for remote deployments
- **⚙️ Flexible Configuration**: Environment variables, config files, and CLI options
- **⚡ Fast & Reliable**: 100% test success rate across all scenarios
- **🌐 Multiple Transports**: stdio (Claude Desktop) and HTTP (web applications)
- **🛡️ Guardrails**: Package allowlist, explicit user approval for file writes, package installs and system calls, and filesystem confinement for tool-written files. These guard against mistakes, not adversaries — RMCP executes R as the invoking user, so run it as a trusted local tool rather than an untrusted multi-tenant service.

## 📚 Documentation

| Resource | Description |
|----------|-------------|
| **[Quick Start Guide](examples/quick_start_guide.md)** | Copy-paste ready examples with real data |
| **[Economic Research Examples](examples/economic_research_example.md)** | Panel data, time series, advanced econometrics |
| **[Time Series Examples](examples/advanced_time_series_example.md)** | ARIMA, forecasting, decomposition |
| **[Image Display Examples](examples/image_display_example.md)** | Inline visualizations in Claude |
| **[API Documentation](docs/)** | Auto-generated API reference |

## 🧪 Validation

RMCP has been tested with real-world scenarios achieving **100% success rate**:

- ✅ **Business Analysts**: Sales forecasting with 97.9% R², $4.70 ROI per marketing dollar
- ✅ **Economists**: Macroeconomic analysis confirming Okun's Law (r=-0.944)
- ✅ **Data Scientists**: Customer churn prediction with 100% accuracy
- ✅ **Researchers**: Treatment effect analysis with significant results (p<0.001)

## 🤝 Contributing

We welcome contributions!

```bash
git clone https://github.com/finite-sample/rmcp.git
cd rmcp
pip install -e ".[dev]"

# Run tests
uv run pytest tests/

# Lint and format
uv run ruff check --fix .
uv run ruff format .
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🛠️ Quick Troubleshooting

**R not found?**
```bash
# macOS: brew install r
# Ubuntu: sudo apt install r-base
R --version
```

**Missing R packages?**
```bash
rmcp check-r-packages  # Check what's missing
```

**MCP connection issues?**
```bash
rmcp list-capabilities   # verify tools register without starting a session
rmcp --debug start       # run the server with verbose logging on stderr
```

**📖 Need more help?** Check the [examples](examples/) directory for working code.

## 🙋 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/finite-sample/rmcp/issues)
- 📖 **Examples**: [Working examples](examples/quick_start_guide.md)

---

**Ready to turn conversations into statistical insights?** Install RMCP and start analyzing data through AI assistants today! 🚀
