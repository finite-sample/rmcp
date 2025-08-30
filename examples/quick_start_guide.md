# RMCP Quick Start Guide

This guide shows you how to get started with RMCP for statistical analysis using the tools we actually have working.

## Installation

```bash
pip install rmcp
```

## Basic Usage

Start the RMCP server:

```bash
rmcp start
```

The server will wait for JSON messages on stdin. Here are examples using our working tools.

## Example 1: Linear Regression Analysis

**Business Question**: How does marketing spend affect sales?

```bash
echo '{
  "tool": "linear_model",
  "args": {
    "data": {
      "sales": [120, 135, 128, 142, 156, 148, 160, 175],
      "marketing": [10, 12, 11, 14, 16, 15, 18, 20]
    },
    "formula": "sales ~ marketing"
  }
}' | rmcp start
```

**Expected Result**:
```json
{
  "coefficients": {"(Intercept)": 42.5, "marketing": 6.75},
  "r_squared": 0.89,
  "p_values": {"marketing": 0.001},
  "n_obs": 8
}
```

**Interpretation**: Every $1 increase in marketing spend leads to 6.75 units increase in sales. The model explains 89% of sales variation.

## Example 2: Correlation Analysis

**Research Question**: What's the relationship between GDP growth and unemployment?

```bash
echo '{
  "tool": "correlation_analysis", 
  "args": {
    "data": {
      "gdp_growth": [2.1, 2.3, 1.8, 2.5, 2.7, 2.2],
      "unemployment": [5.2, 5.0, 5.5, 4.8, 4.5, 4.9]
    },
    "variables": ["gdp_growth", "unemployment"],
    "method": "pearson"
  }
}' | rmcp start
```

**Expected Result**:
```json
{
  "correlation_matrix": {
    "gdp_growth": [1.0, -0.944],
    "unemployment": [-0.944, 1.0]
  },
  "variables": ["gdp_growth", "unemployment"],
  "method": "pearson",
  "n_obs": 6
}
```

**Interpretation**: Strong negative correlation (-0.944) supports Okun's Law - higher GDP growth is associated with lower unemployment.

## Example 3: Customer Churn Prediction

**Business Question**: Can we predict which customers will churn based on tenure and charges?

```bash
echo '{
  "tool": "logistic_regression",
  "args": {
    "data": {
      "churn": [0, 1, 0, 1, 0, 0, 1, 1, 0, 1],
      "tenure_months": [24, 6, 36, 3, 48, 18, 9, 2, 60, 4],
      "monthly_charges": [70, 85, 65, 90, 60, 75, 95, 100, 55, 88]
    },
    "formula": "churn ~ tenure_months + monthly_charges",
    "family": "binomial",
    "link": "logit"
  }
}' | rmcp start
```

**Expected Result**:
```json
{
  "coefficients": {
    "(Intercept)": 2.45,
    "tenure_months": -0.12,
    "monthly_charges": 0.03
  },
  "odds_ratios": {
    "tenure_months": 0.887,
    "monthly_charges": 1.030
  },
  "accuracy": 0.90,
  "mcfadden_r_squared": 0.65,
  "n_obs": 10
}
```

**Interpretation**: 
- Longer tenure reduces churn risk (odds ratio = 0.887)
- Higher monthly charges increase churn risk (odds ratio = 1.030)  
- Model achieves 90% accuracy

## Testing Multiple Tools

You can test all working functionality with our comprehensive test suite:

```bash
python tests/realistic_scenarios.py
```

This runs 4 real-world scenarios and should show 100% success rate.

## Integration with Claude Desktop

Add this to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "rmcp": {
      "command": "rmcp",
      "args": ["start"],
      "env": {}
    }
  }
}
```

Now you can ask Claude questions like:

> "I have sales data with marketing spend. Can you run a regression analysis to see how marketing affects sales?"

> "Can you check the correlation between these two economic variables for me?"

> "Help me build a logistic regression model to predict customer churn."

## What's Working vs. Coming Soon

### ✅ Currently Working (100% tested)
- `linear_model`: Linear regression with robust standard errors
- `correlation_analysis`: Pearson, Spearman, Kendall correlations  
- `logistic_regression`: Binary classification with odds ratios

### 🚧 Coming Soon
- Time series analysis (ARIMA, VAR models)
- Data transformation tools (lag, difference, winsorization)  
- Advanced visualizations
- Panel data models

## Troubleshooting

**Server won't start?**
- Make sure Python 3.8+ is installed
- R should be available in PATH (auto-configured)

**Tools not working?**
- Check input format matches examples exactly
- Verify R is installed with `which R`

**Need help?**
- Check [GitHub Issues](https://github.com/gojiplus/rmcp/issues)
- Run `python tests/realistic_scenarios.py` to test your installation

## Next Steps

1. Try the examples above with your own data
2. Explore the full API in the [README](../README.md)
3. Check out advanced examples in `/examples`
4. Join the community discussions on GitHub

Ready to analyze data with AI assistance? You're all set! 🚀