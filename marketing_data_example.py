#!/usr/bin/env python3
"""
Marketing Data Analysis Example for RMCP v0.3.10
================================================

This example demonstrates comprehensive marketing analysis using RMCP's 40 statistical tools.
Perfect for testing in Claude Desktop after setting up RMCP integration.

Usage: Copy and paste the data and questions below into Claude Desktop
"""

# Sample Marketing Dataset
marketing_data = {
    "month": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "marketing_spend": [5000, 7500, 6000, 8000, 9500, 11000, 8500, 10000, 12000, 9000, 13500, 15000],
    "sales_revenue": [25000, 35000, 30000, 42000, 48000, 55000, 44000, 52000, 61000, 47000, 68000, 76000],
    "customer_satisfaction": [7.2, 7.8, 7.5, 8.1, 8.4, 8.7, 8.2, 8.5, 8.9, 8.3, 9.1, 9.3],
    "website_traffic": [1200, 1800, 1450, 2100, 2400, 2750, 2200, 2600, 3100, 2350, 3400, 3800]
}

print("🎯 RMCP Marketing Analysis Example")
print("=" * 50)

print("\n📊 Dataset Overview:")
print(f"• {len(marketing_data['month'])} months of data")
print(f"• Marketing spend: ${min(marketing_data['marketing_spend']):,} - ${max(marketing_data['marketing_spend']):,}")
print(f"• Sales revenue: ${min(marketing_data['sales_revenue']):,} - ${max(marketing_data['sales_revenue']):,}")
print(f"• Customer satisfaction: {min(marketing_data['customer_satisfaction']):.1f} - {max(marketing_data['customer_satisfaction']):.1f}")
print(f"• Website traffic: {min(marketing_data['website_traffic']):,} - {max(marketing_data['website_traffic']):,}")

print("\n" + "=" * 70)
print("📋 COPY & PASTE THESE EXAMPLES INTO CLAUDE DESKTOP")
print("=" * 70)

examples = [
    {
        "title": "1. 📈 Marketing ROI Analysis",
        "question": """I have marketing data for 12 months. Can you analyze the relationship between marketing spend and sales revenue?

Data:
month: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
marketing_spend: [5000, 7500, 6000, 8000, 9500, 11000, 8500, 10000, 12000, 9000, 13500, 15000]
sales_revenue: [25000, 35000, 30000, 42000, 48000, 55000, 44000, 52000, 61000, 47000, 68000, 76000]

Please calculate ROI and show me a scatter plot with trend line.""",
        "expected": "Linear regression showing ROI per dollar spent, R² value, scatter plot with trend line"
    },
    
    {
        "title": "2. 🔗 Multi-Variable Correlation Analysis", 
        "question": """Can you analyze correlations between all these marketing variables and create a heatmap?

Data:
marketing_spend: [5000, 7500, 6000, 8000, 9500, 11000, 8500, 10000, 12000, 9000, 13500, 15000]
sales_revenue: [25000, 35000, 30000, 42000, 48000, 55000, 44000, 52000, 61000, 47000, 68000, 76000]
customer_satisfaction: [7.2, 7.8, 7.5, 8.1, 8.4, 8.7, 8.2, 8.5, 8.9, 8.3, 9.1, 9.3]
website_traffic: [1200, 1800, 1450, 2100, 2400, 2750, 2200, 2600, 3100, 2350, 3400, 3800]

Which variables are most strongly correlated?""",
        "expected": "Correlation matrix, heatmap visualization, significance tests, insights about strongest relationships"
    },
    
    {
        "title": "3. 📊 Comprehensive Descriptive Statistics",
        "question": """Please provide comprehensive summary statistics for my marketing data:

Data:
marketing_spend: [5000, 7500, 6000, 8000, 9500, 11000, 8500, 10000, 12000, 9000, 13500, 15000]
sales_revenue: [25000, 35000, 30000, 42000, 48000, 55000, 44000, 52000, 61000, 47000, 68000, 76000]
customer_satisfaction: [7.2, 7.8, 7.5, 8.1, 8.4, 8.7, 8.2, 8.5, 8.9, 8.3, 9.1, 9.3]

Include outlier detection and frequency analysis.""",
        "expected": "Mean, median, std dev, quartiles, outlier detection results, distribution analysis"
    },
    
    {
        "title": "4. ⏱️ Time Series Trend Analysis",
        "question": """Analyze the time series trend in my sales data and forecast next 3 months:

Data:
month: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
sales_revenue: [25000, 35000, 30000, 42000, 48000, 55000, 44000, 52000, 61000, 47000, 68000, 76000]

Is there a clear trend? Can you predict months 13, 14, 15?""",
        "expected": "Time series decomposition, trend analysis, ARIMA forecasting with confidence intervals"
    },
    
    {
        "title": "5. 🎯 Marketing Effectiveness Test",
        "question": """I want to test if months with above-average marketing spend have significantly higher sales. 

Data:
marketing_spend: [5000, 7500, 6000, 8000, 9500, 11000, 8500, 10000, 12000, 9000, 13500, 15000]
sales_revenue: [25000, 35000, 30000, 42000, 48000, 55000, 44000, 52000, 61000, 47000, 68000, 76000]

Please run appropriate statistical tests.""",
        "expected": "Two-sample t-test comparing high vs low marketing spend groups, significance tests"
    }
]

for i, example in enumerate(examples, 1):
    print(f"\n{example['title']}")
    print("-" * 50)
    print(f"Question to ask Claude:")
    print(f'"{example["question"]}"')
    print(f"\nExpected Output: {example['expected']}")
    print()

print("\n" + "=" * 70)
print("🚀 TESTING TIPS")
print("=" * 70)
print("• Start with Example 1 for basic ROI analysis")
print("• Each example tests different RMCP capabilities")
print("• All visualizations will appear directly in Claude chat")
print("• Look for inline plots, statistical summaries, and insights")
print("• Try follow-up questions like 'Create a histogram of sales' or 'Test for normality'")

print("\n✅ RMCP v0.3.10 Features Tested:")
print("• Linear regression (ROI analysis)")
print("• Correlation analysis with heatmaps") 
print("• Summary statistics and outlier detection")
print("• Time series analysis and forecasting")
print("• Statistical hypothesis testing")
print("• Interactive data visualization")

if __name__ == "__main__":
    print(f"\n🎉 Ready to test RMCP! Copy examples above into Claude Desktop.")