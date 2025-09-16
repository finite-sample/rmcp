"""
RMCP Streamlit Cloud App
Interactive econometric analysis interface powered by Claude AI.

This is a cloud-compatible version that demonstrates RMCP capabilities
without requiring the local R/RMCP installation.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import tempfile
import os
from datetime import datetime, timedelta

# Anthropic Claude API
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    st.error("Please install the Anthropic SDK: `pip install anthropic`")

# Page config
st.set_page_config(
    page_title="RMCP - R Econometrics with Claude AI", 
    page_icon="📊",
    layout="wide"
)

# Header
st.title("📊 RMCP - R Econometrics with Claude AI")
st.markdown("*Advanced econometric analysis with R, powered by Claude AI assistance*")

# Information about this demo
st.info("""
🌟 **Welcome to the RMCP Demo!** 

This is a demonstration version running on Streamlit Community Cloud. 
For the full experience with R-powered econometric analysis, you can:

- 📦 Install RMCP locally: `pip install rmcp`
- 🔧 Run locally: `rmcp start` 
- 🖥️ Use Claude Desktop with MCP integration

**Current demo features:**
- 🤖 Claude AI assistance for econometric questions
- 📊 Sample data generation and exploration
- 📈 Basic statistical analysis with Python
- 💡 Econometric method recommendations
""")

# Sidebar for API key
st.sidebar.title("🔧 Configuration")

# Claude API Key input
if ANTHROPIC_AVAILABLE:
    api_key = st.sidebar.text_input(
        "Claude API Key", 
        type="password",
        help="Enter your Anthropic Claude API key from https://console.anthropic.com/"
    )
    
    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
        st.sidebar.success("✅ Claude API connected")
    else:
        st.sidebar.warning("⚠️ Please enter your Claude API key")
        client = None
else:
    client = None

# RMCP Tools Overview
st.sidebar.subheader("🛠️ RMCP Tool Categories")
st.sidebar.markdown("""
**📈 Descriptive Statistics**
- Summary statistics, correlations, outliers

**📊 Regression Analysis** 
- Linear, logistic, panel models

**🧪 Statistical Tests**
- T-tests, ANOVA, normality tests

**📉 Time Series & Econometrics**
- ARIMA, VAR, panel regression, IV

**🔄 Data Transformations**
- Lags, differences, winsorization

**📊 Visualizations**
- Plots, heatmaps, diagnostics

**🤖 Machine Learning**
- Clustering, trees, random forest
""")

# Sample data generation
st.subheader("📚 Sample Economic Data")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 Generate Economic Panel Data"):
        # Create sample economic dataset
        np.random.seed(42)
        
        countries = ['USA', 'GER', 'JPN', 'UK', 'FRA', 'ITA', 'CAN', 'AUS']
        years = list(range(2000, 2024))
        
        data_rows = []
        for country in countries:
            for year in years:
                # Create realistic economic relationships
                base_gdp = np.random.normal(2.5, 1.0)
                unemployment = max(0.5, np.random.normal(5.5, 2.0))
                inflation = max(0, np.random.normal(2.5, 1.5))
                
                # GDP growth negatively correlated with unemployment
                gdp_growth = base_gdp - 0.3 * (unemployment - 5.5) + np.random.normal(0, 0.5)
                
                data_rows.append({
                    'country': country,
                    'year': year,
                    'gdp_growth': round(gdp_growth, 2),
                    'unemployment': round(unemployment, 2),
                    'inflation': round(inflation, 2),
                    'interest_rate': round(max(0, np.random.normal(2.0, 1.0)), 2),
                    'debt_to_gdp': round(max(20, np.random.normal(60, 20)), 1)
                })
        
        sample_data = pd.DataFrame(data_rows)
        st.session_state['sample_data'] = sample_data
        
        st.success("✅ Economic panel data generated!")
        st.dataframe(sample_data.head(10))
        
        # Basic analysis
        st.write("**Quick Analysis:**")
        st.write(f"- {len(sample_data)} observations across {len(countries)} countries")
        st.write(f"- Time period: {min(years)}-{max(years)}")
        st.write(f"- Average GDP growth: {sample_data['gdp_growth'].mean():.2f}%")
        st.write(f"- Average unemployment: {sample_data['unemployment'].mean():.2f}%")

with col2:
    if st.button("📈 Generate Time Series Data"):
        # Create sample time series
        np.random.seed(123)
        dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
        
        # Simulated economic indicators with trends and seasonality
        trend = np.linspace(100, 120, len(dates))
        seasonal = 5 * np.sin(2 * np.pi * np.arange(len(dates)) / 365.25)
        noise = np.random.normal(0, 2, len(dates))
        
        ts_data = pd.DataFrame({
            'date': dates,
            'stock_index': trend + seasonal + noise,
            'gdp_index': trend * 0.8 + np.random.normal(0, 1, len(dates)),
            'unemployment_rate': 5 + np.sin(2 * np.pi * np.arange(len(dates)) / 365.25) + np.random.normal(0, 0.5, len(dates)),
            'inflation_rate': 2.5 + 0.3 * np.sin(2 * np.pi * np.arange(len(dates)) / 365.25) + np.random.normal(0, 0.3, len(dates))
        })
        
        st.session_state['ts_data'] = ts_data
        
        st.success("✅ Time series data generated!")
        st.line_chart(ts_data.set_index('date')[['stock_index', 'gdp_index']])

with col3:
    if st.button("🏦 Generate Financial Data"):
        # Create sample financial dataset
        np.random.seed(456)
        n = 1000
        
        # Simulated bank data
        financial_data = pd.DataFrame({
            'bank_id': range(1, n+1),
            'total_assets': np.random.lognormal(15, 1.5, n),
            'total_loans': np.random.lognormal(14, 1.2, n),
            'deposits': np.random.lognormal(14.5, 1.3, n),
            'net_income': np.random.normal(50, 25, n),
            'loan_loss_provision': np.random.exponential(5, n),
            'tier1_capital_ratio': np.random.normal(12, 3, n),
            'roa': np.random.normal(1.2, 0.8, n),
            'roe': np.random.normal(8, 4, n),
            'region': np.random.choice(['North', 'South', 'East', 'West'], n)
        })
        
        # Ensure realistic relationships
        financial_data['total_loans'] = np.minimum(financial_data['total_loans'], 
                                                  financial_data['total_assets'] * 0.8)
        financial_data['tier1_capital_ratio'] = np.maximum(8, financial_data['tier1_capital_ratio'])
        
        st.session_state['financial_data'] = financial_data
        
        st.success("✅ Financial dataset generated!")
        st.dataframe(financial_data.head(10))

# Data upload section
st.subheader("📁 Data Upload & Analysis")

uploaded_file = st.file_uploader(
    "Upload your dataset (CSV format)", 
    type=['csv'],
    help="Upload a CSV file for analysis"
)

# Use uploaded data or sample data
data = None
if uploaded_file is not None:
    try:
        data = pd.read_csv(uploaded_file)
        st.success(f"✅ Data loaded: {data.shape[0]} rows, {data.shape[1]} columns")
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")

elif 'sample_data' in st.session_state:
    if st.checkbox("Use generated economic panel data"):
        data = st.session_state['sample_data']
        st.success(f"✅ Using sample data: {data.shape[0]} rows, {data.shape[1]} columns")

elif 'ts_data' in st.session_state:
    if st.checkbox("Use generated time series data"):
        data = st.session_state['ts_data']
        st.success(f"✅ Using time series data: {data.shape[0]} rows, {data.shape[1]} columns")

elif 'financial_data' in st.session_state:
    if st.checkbox("Use generated financial data"):
        data = st.session_state['financial_data']
        st.success(f"✅ Using financial data: {data.shape[0]} rows, {data.shape[1]} columns")

# Data exploration
if data is not None:
    with st.expander("📋 Data Preview & Info"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📊 Data Preview:**")
            st.dataframe(data.head())
            
        with col2:
            st.write("**ℹ️ Data Info:**")
            st.write(f"Shape: {data.shape}")
            st.write("**Column Types:**")
            st.write(data.dtypes)
            
            if data.isnull().sum().sum() > 0:
                st.write("**Missing Values:**")
                st.write(data.isnull().sum())
    
    # Basic statistical analysis
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        st.subheader("📈 Basic Statistical Analysis")
        
        selected_vars = st.multiselect(
            "Select variables for analysis:", 
            numeric_cols, 
            default=numeric_cols[:4] if len(numeric_cols) >= 4 else numeric_cols
        )
        
        if selected_vars:
            # Summary statistics
            st.write("**📊 Summary Statistics:**")
            summary_stats = data[selected_vars].describe()
            st.dataframe(summary_stats)
            
            # Correlation matrix
            if len(selected_vars) > 1:
                st.write("**🔗 Correlation Matrix:**")
                corr_matrix = data[selected_vars].corr()
                st.dataframe(corr_matrix)
                
                # Simple visualization
                st.write("**📈 Data Visualization:**")
                chart_type = st.selectbox("Chart type:", ["Line Chart", "Scatter Plot", "Histogram"])
                
                if chart_type == "Line Chart" and len(selected_vars) >= 2:
                    st.line_chart(data[selected_vars])
                elif chart_type == "Scatter Plot" and len(selected_vars) >= 2:
                    x_var = st.selectbox("X variable:", selected_vars)
                    y_var = st.selectbox("Y variable:", [v for v in selected_vars if v != x_var])
                    if x_var and y_var:
                        st.scatter_chart(data, x=x_var, y=y_var)
                elif chart_type == "Histogram":
                    hist_var = st.selectbox("Variable for histogram:", selected_vars)
                    if hist_var:
                        st.bar_chart(data[hist_var].value_counts().head(20))

# Claude AI Assistant
if client:
    st.subheader("🤖 Claude AI Econometric Assistant")
    
    # Predefined econometric questions
    st.write("**💡 Quick Questions:**")
    quick_questions = [
        "What econometric method should I use for panel data analysis?",
        "How do I test for multicollinearity in my regression?", 
        "What's the difference between fixed effects and random effects?",
        "How do I interpret instrumental variables regression results?",
        "What diagnostic tests should I run after regression analysis?",
        "How do I handle heteroskedasticity in my model?",
        "What's the best way to test for stationarity in time series?",
        "How do I choose the right ARIMA model order?"
    ]
    
    selected_question = st.selectbox("Choose a question:", [""] + quick_questions)
    
    user_question = st.text_area(
        "Or ask your own question about econometrics:",
        value=selected_question,
        placeholder="e.g., 'How do I handle endogeneity in my regression model?'"
    )
    
    if st.button("💬 Ask Claude") and user_question:
        try:
            with st.spinner("🤔 Claude is thinking..."):
                # Prepare context about the data if available
                data_context = ""
                if data is not None:
                    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
                    categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
                    
                    data_context = f"""
                    User's Dataset Context:
                    - Shape: {data.shape[0]} rows, {data.shape[1]} columns
                    - Numeric columns: {', '.join(numeric_cols)} 
                    - Categorical columns: {', '.join(categorical_cols)}
                    - Sample data preview: {data.head(3).to_dict()}
                    """
                
                econometric_context = """
                You are an expert econometrician helping with RMCP (R Model Context Protocol) - a tool that provides advanced econometric analysis capabilities including:
                
                Key RMCP capabilities:
                - Linear and nonlinear regression models
                - Panel data analysis (fixed effects, random effects, dynamic panels)
                - Time series analysis (ARIMA, VAR, cointegration tests)
                - Instrumental variables and causal inference methods
                - Advanced diagnostics (heteroskedasticity, autocorrelation, specification tests)
                - Machine learning approaches for econometrics
                - Comprehensive visualization tools
                
                Please provide practical, actionable advice for econometric analysis.
                """
                
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1500,
                    messages=[{
                        "role": "user", 
                        "content": f"{econometric_context}\n\n{data_context}\n\nUser question: {user_question}"
                    }]
                )
                
                st.write("**Claude's Response:**")
                st.write(message.content[0].text)
                
        except Exception as e:
            st.error(f"❌ Error communicating with Claude: {e}")

else:
    st.info("🔑 Enter your Claude API key in the sidebar to enable AI assistance")

# RMCP Installation Instructions
st.subheader("🚀 Get the Full RMCP Experience")

st.markdown("""
To access all RMCP's powerful econometric capabilities locally:

### 📦 Installation
```bash
pip install rmcp
```

### 🔧 Usage
```bash
# Start RMCP server
rmcp start

# List available tools
rmcp list-capabilities

# Use with Claude Desktop (MCP integration)
# Add to claude_desktop_config.json:
{
  "mcpServers": {
    "rmcp": {
      "command": "rmcp",
      "args": ["start"]
    }
  }
}
```

### 🛠️ Available Analysis Tools
- **33+ statistical and econometric tools**
- **R-powered backend** for advanced analysis
- **Professional visualizations** with ggplot2
- **Comprehensive diagnostics** and model validation
- **Export capabilities** for research papers

### 📖 Documentation
- GitHub: [github.com/your-repo/rmcp](https://github.com)
- Documentation: Full API reference and examples
- Examples: Real-world econometric analysis workflows
""")

# Footer
st.markdown("---")
st.markdown("""
**About RMCP:**
RMCP (R Model Context Protocol) bridges the gap between AI assistants and professional econometric analysis. 
Built for researchers, analysts, and students who need robust statistical computing with modern AI assistance.

*This demo showcases RMCP's potential. Install locally for the complete R-powered experience.*
""")

# Download links for sample data
if 'sample_data' in st.session_state:
    st.download_button(
        "📥 Download Economic Panel Data",
        data=st.session_state['sample_data'].to_csv(index=False),
        file_name="economic_panel_data.csv",
        mime="text/csv"
    )

if 'ts_data' in st.session_state:
    st.download_button(
        "📥 Download Time Series Data", 
        data=st.session_state['ts_data'].to_csv(index=False),
        file_name="time_series_data.csv",
        mime="text/csv"
    )

if 'financial_data' in st.session_state:
    st.download_button(
        "📥 Download Financial Data",
        data=st.session_state['financial_data'].to_csv(index=False), 
        file_name="financial_data.csv",
        mime="text/csv"
    )