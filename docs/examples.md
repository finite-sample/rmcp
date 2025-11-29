# Examples and Use Cases

Comprehensive examples showing RMCP capabilities across different statistical analysis scenarios.

## Quick Start Examples

For immediate hands-on experience, see:
- [Quick Start Guide](../examples/quick_start_guide.md) - Basic usage examples
- [Working Examples →](../examples/quick_start_guide.md) - Get started immediately

## Advanced Statistical Analysis

### Time Series Analysis
[Advanced Time Series Example](../examples/advanced_time_series_example.md)
- ARIMA modeling and forecasting
- Seasonal decomposition
- Stationarity testing
- Economic forecasting workflows

### Economic Research
[Economic Research Example](../examples/economic_research_example.md)
- Panel data analysis
- Instrumental variables
- Policy impact analysis
- Econometric modeling workflows

### Claude Desktop Integration
[Claude Desktop Examples](../examples/claude_desktop_v0.5.0_examples.md)
- Interactive statistical analysis
- Real-time visualizations
- Data exploration workflows
- Advanced statistical conversations

## Statistical Categories

### Regression & Economics
```markdown
"Analyze the relationship between marketing spend and ROI"
"Run a panel data regression with fixed effects"
"Test for endogeneity using instrumental variables"
```

### Time Series & Forecasting
```markdown
"Forecast next quarter's sales using ARIMA"
"Decompose the time series into trend and seasonal components"
"Test if the series is stationary"
```

### Machine Learning
```markdown
"Cluster customers by purchasing behavior"
"Build a decision tree to predict churn"
"What are the most important features?"
```

### Statistical Testing
```markdown
"Is my A/B test result statistically significant?"
"Run an ANOVA to compare group means"
"Test if the data follows a normal distribution"
```

### Data Analysis & Visualization
```markdown
"Summarize this dataset with descriptive statistics"
"Create a correlation heatmap"
"Generate a professional scatter plot"
```

## Working with Data

### File Formats Supported
- **CSV files**: `read_csv()`, `write_csv()`
- **Excel files**: `read_excel()`, `write_excel()`
- **JSON data**: `read_json()`, `write_json()`
- **Direct data input**: Arrays, matrices

### Data Transformation
```markdown
"Standardize the variables"
"Create lag variables for time series"
"Winsorize outliers at 5th and 95th percentiles"
"Filter data where income > 50000"
```

## Interactive Examples

All examples are designed to work with:
- **Claude Desktop** - Local MCP integration
- **Claude Web** - HTTP server integration
- **Direct API calls** - Programmatic access
- **Jupyter notebooks** - Data science workflows

## Example Data Sets

RMCP includes several example datasets for testing:
- Economic indicators
- Panel data
- Time series data
- Customer behavior data
- Sales and marketing data

Access via: `load_example("dataset_name")`

## Best Practices

### Effective Prompts
- Be specific about the analysis you want
- Mention the statistical method if you know it
- Specify output format preferences
- Ask for interpretations and insights

### Error Recovery
- RMCP provides intelligent error diagnosis
- Suggested fixes for common issues
- Alternative approaches when methods fail
- Data validation and cleaning suggestions

### Visualization
- Plots are displayed inline in conversations
- Professional styling with ggplot2
- Export capabilities (PNG, PDF, SVG)
- Customizable themes and colors
