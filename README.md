# RMCP: Statistical Analysis through Natural Conversation

[![Python application](https://github.com/finite-sample/rmcp/actions/workflows/ci.yml/badge.svg)](https://github.com/finite-sample/rmcp/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/rmcp.svg)](https://pypi.org/project/rmcp/)
[![Downloads](https://pepy.tech/badge/rmcp)](https://pepy.tech/project/rmcp)
[![Documentation](https://github.com/finite-sample/rmcp/actions/workflows/docs.yml/badge.svg)](https://finite-sample.github.io/rmcp/)
[![License](https://img.shields.io/github/license/finite-sample/rmcp)](https://github.com/finite-sample/rmcp/blob/main/LICENSE)

**Turn conversations into comprehensive statistical analysis** - A Model Context Protocol (MCP) server with **52 statistical analysis tools** across 11 categories and **429 R packages** from systematic CRAN task views. RMCP enables AI assistants to perform sophisticated statistical modeling, econometric analysis, machine learning, time series analysis, and data science tasks through natural conversation.

## 🚀 Quick Start (30 seconds)

### 🌐 **Try the Live Server** (No Installation Required)

**HTTP Server**: `https://rmcp-server-394229601724.us-central1.run.app/mcp`
**Interactive Docs**: `https://rmcp-server-394229601724.us-central1.run.app/docs`
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
- **Python 3.10+**
- **R 4.4.0+** with **comprehensive package ecosystem**: RMCP uses a systematic 429-package whitelist from CRAN task views organized into 19+ categories:

```r
# Core packages (install these first)
install.packages(c(
  "jsonlite", "dplyr", "ggplot2", "broom", "plm", "forecast",
  "randomForest", "rpart", "caret", "AER", "vars", "mgcv"
))

# Full ecosystem automatically available: Machine Learning (61 packages),
# Econometrics (55 packages), Time Series (48 packages),
# Bayesian Analysis (32 packages), and more
```

**Package Selection**: Evidence-based using CRAN task views, download statistics, and 4-tier security assessment

### Install RMCP

```bash
# Standard installation
pip install rmcp

# With HTTP transport support
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

**Production Server** (ready to use):
```
Server URL: https://rmcp-server-394229601724.us-central1.run.app/mcp
Interactive Docs: https://rmcp-server-394229601724.us-central1.run.app/docs
```

**Test the connection**:
```bash
# Health check
curl https://rmcp-server-394229601724.us-central1.run.app/health

# Initialize MCP session
curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
  -H "Content-Type: application/json" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0"}}}'
```

**Local HTTP server**:
```bash
# Start local HTTP server
rmcp serve-http --host 0.0.0.0 --port 8080

# Access at: http://localhost:8080/docs
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
- **📚 Comprehensive Package Ecosystem**: 429 R packages from systematic CRAN task views with 4-tier security system
- **📊 Professional Output**: Formatted results with markdown tables and inline visualizations
- **🔒 Production Ready**: Full MCP protocol compliance with HTTP transport and SSE
- **⚙️ Flexible Configuration**: Environment variables, config files, and CLI options
- **⚡ Fast & Reliable**: 100% test success rate across all scenarios
- **🌐 Multiple Transports**: stdio (Claude Desktop) and HTTP (web applications)
- **🛡️ Secure**: Evidence-based package selection with security-conscious permission tiers

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
python tests/unit/test_new_tools.py
python tests/e2e/test_claude_desktop_scenarios.py

# Format code
black rmcp/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

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
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | rmcp start
```

**📖 Need more help?** Check the [examples](examples/) directory for working code.

## 🙋 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/finite-sample/rmcp/issues)
- 📖 **Examples**: [Working examples](examples/quick_start_guide.md)

---

**Ready to turn conversations into statistical insights?** Install RMCP and start analyzing data through AI assistants today! 🚀
# Test comment
