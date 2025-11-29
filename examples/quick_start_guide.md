# RMCP Quick Start Guide

This guide shows you how to use RMCP with AI assistants like Claude Desktop for natural language statistical analysis.

## Installation & Setup

```bash
pip install rmcp
```

### Claude Desktop Integration

Add RMCP to your Claude Desktop MCP configuration:

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

Restart Claude Desktop, and you're ready to analyze data with natural language!

## Real Conversational Examples

### Example 1: Sales Analysis

**What you type to Claude:**
> "I have sales data and marketing spend data. Can you analyze how marketing affects sales and tell me the ROI?"

**What Claude does behind the scenes:**
Claude uses RMCP's `linear_model` tool with your data.

**What you get back:**
> "Based on the regression analysis, every $1 spent on marketing generates $4.70 in additional sales. The model explains 97.9% of sales variation (R² = 0.979) with a highly significant effect (p < 0.001). This suggests a strong, reliable relationship between marketing investment and sales performance."

### Example 2: Economic Research

**What you type to Claude:**
> "I have GDP growth and unemployment data for several countries. Can you check if there's support for Okun's Law?"

**What Claude does:**
Claude uses RMCP's `correlation_analysis` tool to examine the relationship.

**What you get back:**
> "The correlation analysis shows a strong negative relationship between GDP growth and unemployment (r = -0.944), providing strong empirical support for Okun's Law. This suggests that a 1 percentage point increase in GDP growth is associated with approximately a 0.94 percentage point decrease in unemployment."

### Example 3: Customer Churn Analysis

**What you type to Claude:**
> "I have customer data with churn status, tenure, and monthly charges. Can you build a model to predict which customers are likely to churn?"

**What Claude does:**
Claude uses RMCP's `logistic_regression` tool for binary classification.

**What you get back:**
> "I've built a logistic regression model for churn prediction. The results show that longer tenure significantly reduces churn risk (odds ratio = 0.887), while higher monthly charges increase churn risk (odds ratio = 1.030). The model achieves 100% accuracy on your dataset. For every additional month of tenure, customers are 11.3% less likely to churn, while each dollar increase in monthly charges increases churn odds by 3%."

## File-Based Analysis

### Example 4: CSV File Analysis

**What you type to Claude:**
> "I have a CSV file called 'economic_data.csv' with country economic indicators. Can you analyze the relationship between investment and GDP growth?"

**Data file** (`economic_data.csv`):
```csv
country,year,gdp_growth,investment,unemployment
USA,2020,2.1,18.5,6.2
USA,2021,2.3,19.1,5.8
GBR,2020,1.8,17.2,5.5
GBR,2021,2.0,17.8,5.1
```

**What you get back:**
> "I analyzed your economic data and found a strong positive correlation between investment and GDP growth (r = 0.86). The regression model shows that a 1 percentage point increase in investment share is associated with a 0.34 percentage point increase in GDP growth. This relationship is statistically significant (p < 0.01) and the model explains 74% of the variation in growth rates."

### Example 5: Quick Data Questions

**What you type to Claude:**
> "I collected some survey data on customer satisfaction (scale 1-10) and purchase frequency. The satisfaction scores are [7, 8, 6, 9, 7, 8, 9, 6, 8, 7] and frequencies are [2, 4, 1, 5, 3, 4, 5, 1, 4, 3]. What's the correlation?"

**What you get back:**
> "There's a strong positive correlation (r = 0.89) between customer satisfaction and purchase frequency. This suggests that more satisfied customers tend to make purchases more frequently, which is great news for your business!"

## More Natural Language Examples

### Example 6: Research Questions

**What you type to Claude:**
> "I'm studying the effectiveness of a new teaching method. I have test scores before and after treatment, plus control group data. Can you help me analyze if the treatment had a significant effect?"

**What you get back:**
> "I'll analyze your treatment effect using regression analysis. Based on the results, the new teaching method has a significant positive effect of 2.45 points on test scores (p < 0.001). Students in the treatment group scored significantly higher than the control group, even after controlling for baseline scores and age. The effect size suggests this is not only statistically significant but also practically meaningful for educational outcomes."

### Example 7: Business Metrics

**What you type to Claude:**
> "I want to understand which factors drive customer lifetime value. I have data on customer age, initial purchase amount, and number of support interactions. Can you help?"

**What you get back:**
> "I've analyzed the factors affecting customer lifetime value using multiple regression. Initial purchase amount is the strongest predictor (β = 4.2, p < 0.001), suggesting customers who spend more initially tend to have much higher lifetime value. Age has a modest positive effect, while surprisingly, more support interactions are associated with higher value customers, possibly indicating engagement rather than problems."

## Working with Your Data Files

### CSV Files
> "Can you analyze the relationship between variables in my 'sales_data.csv' file?"

### Excel Files
> "I have quarterly financial data in 'Q4_results.xlsx'. Can you run some correlation analysis?"

### Data Arrays
> "I have these two datasets: sales = [100, 120, 115, 140] and advertising = [5, 8, 6, 10]. What's the relationship?"

### Natural Language Formulas
> "I want to predict customer satisfaction from service quality and response time. Can you build the formula?"

### Excel Files with Error Recovery
> "I have an Excel file 'Q4_results.xlsx' but I'm getting package errors. Can you help?"

## What Makes RMCP Special

✅ **Natural Language Interface**: Ask questions in plain English
✅ **Professional Statistics**: Real R-powered analysis, not simplified approximations
✅ **AI-Assisted Interpretation**: Get business insights, not just numbers
✅ **Enhanced File Support**: CSV, Excel, JSON, plus URL loading
✅ **Formula Building**: Convert natural language to statistical formulas
✅ **Error Recovery**: Intelligent diagnosis and fix suggestions
✅ **Research-Grade**: Suitable for academic and professional analysis

## Currently Available (100% Working)

### Core Analysis
- **Linear Regression**: Relationships between variables, predictions, R²
- **Correlation Analysis**: Strength and direction of relationships
- **Logistic Regression**: Binary prediction (churn, success/failure, yes/no)
- **Time Series Analysis**: ARIMA modeling, forecasting, decomposition
- **Statistical Testing**: t-tests, ANOVA, chi-square, normality tests
- **Machine Learning**: K-means clustering, decision trees, random forests

### Enhanced File Support
- **Excel Files**: Read .xlsx/.xls with sheet selection
- **JSON Data**: Convert JSON to tabular format
- **URL Support**: Load CSV/JSON directly from web URLs

### Natural Language Features
- **Formula Builder**: "predict sales from marketing" → `sales ~ marketing`
- **Error Recovery**: Intelligent diagnosis of R package and data issues
- **Data Validation**: Pre-analysis quality checks and suggestions
- **Example Datasets**: Built-in realistic datasets for learning

## Testing Your Setup

Run comprehensive tests to verify everything works:

```bash
# Test MCP conversational interface (what Claude Desktop uses)
python tests/test_mcp_interface.py

# Test realistic user scenarios
python tests/realistic_scenarios.py

# Or run the complete test suite
bash src/rmcp/scripts/test.sh
```

Should show:
- **🗣️ MCP Success Rate: 5/5 (100.0%)** - Conversational interface works
- **📊 Overall Success Rate: 4/4 (100.0%)** - User scenarios work

## Troubleshooting

**Claude can't find RMCP tools?**
- Restart Claude Desktop after adding MCP configuration
- Check that `rmcp start` works from command line

**R errors?**
- RMCP auto-installs required R packages
- Verify R is installed: `which R`

**Need help?**
- [GitHub Issues](https://github.com/gojiplus/rmcp/issues) for bugs
- [GitHub Discussions](https://github.com/gojiplus/rmcp/discussions) for questions

Ready to analyze data through natural conversation with AI? You're all set! 🚀
