"""
RMCP Streamlit App
Interactive econometric analysis interface powered by Claude AI and R.
"""

import streamlit as st
import pandas as pd
import json
import tempfile
import os
import asyncio
from pathlib import Path

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

# Sidebar for API key and tool selection
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

# Available RMCP tools
AVAILABLE_TOOLS = {
    "📈 Descriptive Statistics": {
        "Summary Statistics": "summary_stats",
        "Outlier Detection": "outlier_detection", 
        "Frequency Table": "frequency_table",
        "Correlation Analysis": "correlation_analysis",
    },
    "📊 Regression Analysis": {
        "Linear Model": "linear_model",
        "Logistic Regression": "logistic_regression",
    },
    "🧪 Statistical Tests": {
        "T-Test": "t_test",
        "ANOVA": "anova",
        "Chi-Square Test": "chi_square_test",
        "Normality Test": "normality_test",
    },
    "📉 Time Series & Econometrics": {
        "ARIMA Model": "arima_model",
        "Panel Regression": "panel_regression",
        "Instrumental Variables": "instrumental_variables",
        "VAR Model": "var_model",
        "Time Series Decomposition": "decompose_timeseries",
        "Stationarity Test": "stationarity_test",
    },
    "🔄 Data Transformations": {
        "Lag/Lead Variables": "lag_lead",
        "Winsorize Data": "winsorize",
        "Difference Variables": "difference", 
        "Standardize Data": "standardize",
    },
    "📊 Visualizations": {
        "Scatter Plot": "scatter_plot",
        "Histogram": "histogram",
        "Box Plot": "boxplot",
        "Time Series Plot": "time_series_plot",
        "Correlation Heatmap": "correlation_heatmap",
        "Regression Plot": "regression_plot",
    },
    "🤖 Machine Learning": {
        "K-Means Clustering": "kmeans_clustering",
        "Decision Tree": "decision_tree",
        "Random Forest": "random_forest",
    },
    "📁 Data Operations": {
        "Read CSV": "read_csv",
        "Write CSV": "write_csv",
        "Data Info": "data_info",
        "Filter Data": "filter_data",
    }
}

# Tool selection
st.sidebar.subheader("🛠️ Select Analysis Tool")
selected_category = st.sidebar.selectbox("Category", list(AVAILABLE_TOOLS.keys()))
tool_options = AVAILABLE_TOOLS[selected_category]
selected_tool_name = st.sidebar.selectbox("Tool", list(tool_options.keys()))
selected_tool_id = tool_options[selected_tool_name]

# Main app
st.title("📊 RMCP - R Econometrics with Claude AI")
st.markdown("*Advanced econometric analysis with R, powered by Claude AI assistance*")

# File upload
st.subheader("📁 Data Upload")
uploaded_file = st.file_uploader(
    "Upload your dataset (CSV format)", 
    type=['csv'],
    help="Upload a CSV file with your data for analysis"
)

data = None
if uploaded_file is not None:
    try:
        data = pd.read_csv(uploaded_file)
        st.success(f"✅ Data loaded: {data.shape[0]} rows, {data.shape[1]} columns")
        
        # Show data preview
        with st.expander("📋 Data Preview"):
            st.dataframe(data.head(10))
            
        with st.expander("ℹ️ Data Info"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Column Types:**")
                st.write(data.dtypes)
            with col2:
                st.write("**Missing Values:**")
                st.write(data.isnull().sum())
                
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")

# Tool interface
st.subheader(f"🔧 {selected_tool_name}")

if data is not None:
    # Create form for tool parameters
    with st.form(f"{selected_tool_id}_form"):
        params = {}
        
        # We'll convert data to dict format for RMCP tools
        
        # Column selectors
        columns = data.columns.tolist()
        numeric_columns = data.select_dtypes(include=['number']).columns.tolist()
        categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Tool-specific parameter forms
        if selected_tool_id == "summary_stats":
            params['variables'] = st.multiselect("Variables to analyze", numeric_columns, default=numeric_columns[:5] if len(numeric_columns) >= 5 else numeric_columns)
            if categorical_columns:
                params['group_by'] = st.selectbox("Group by (optional)", [''] + categorical_columns)
        
        elif selected_tool_id == "outlier_detection":
            params['variable'] = st.selectbox("Variable for outlier detection", numeric_columns)
            params['method'] = st.selectbox("Detection method", ["iqr", "z_score", "modified_z"])
            params['threshold'] = st.number_input("Threshold", min_value=1.0, max_value=5.0, value=3.0)
        
        elif selected_tool_id == "correlation_analysis":
            params['variables'] = st.multiselect("Variables for correlation", numeric_columns, default=numeric_columns[:5] if len(numeric_columns) >= 5 else numeric_columns)
            params['method'] = st.selectbox("Correlation method", ["pearson", "spearman", "kendall"])
        
        elif selected_tool_id == "linear_model":
            params['dependent_var'] = st.selectbox("Dependent Variable", numeric_columns)
            remaining_vars = [col for col in numeric_columns if col != params['dependent_var']]
            params['independent_vars'] = st.multiselect("Independent Variables", remaining_vars)
            params['robust_se'] = st.checkbox("Robust Standard Errors")
        
        elif selected_tool_id == "t_test":
            params['variable'] = st.selectbox("Test Variable", numeric_columns)
            params['test_type'] = st.selectbox("Test Type", ["one_sample", "two_sample", "paired"])
            if params['test_type'] != 'one_sample' and categorical_columns:
                params['group_variable'] = st.selectbox("Group Variable", categorical_columns)
            if params['test_type'] == 'one_sample':
                params['mu'] = st.number_input("Test value (μ)", value=0.0)
        
        elif selected_tool_id in ["scatter_plot", "regression_plot"]:
            params['x_variable'] = st.selectbox("X Variable", numeric_columns)
            remaining_vars = [col for col in numeric_columns if col != params['x_variable']]
            params['y_variable'] = st.selectbox("Y Variable", remaining_vars)
            if categorical_columns:
                params['group_variable'] = st.selectbox("Group Variable (optional)", [''] + categorical_columns)
        
        elif selected_tool_id == "histogram":
            params['variable'] = st.selectbox("Variable", numeric_columns)
            params['bins'] = st.slider("Number of bins", 10, 100, 30)
        
        elif selected_tool_id == "arima_model":
            params['variable'] = st.selectbox("Time Series Variable", numeric_columns)
            if 'date' in str(columns).lower() or 'time' in str(columns).lower():
                date_cols = [col for col in columns if 'date' in col.lower() or 'time' in col.lower()]
                if date_cols:
                    params['time_variable'] = st.selectbox("Time Variable", date_cols)
        
        elif selected_tool_id == "lag_lead":
            params['variables'] = st.multiselect("Variables to lag", numeric_columns)
            params['lags'] = st.number_input("Number of lags", min_value=1, max_value=20, value=1)
        
        # Advanced options
        with st.expander("⚙️ Advanced Options"):
            if selected_tool_id in ["summary_stats", "correlation_analysis"]:
                params['confidence_level'] = st.slider("Confidence Level", 0.8, 0.99, 0.95)
        
        # Submit button
        submitted = st.form_submit_button("🚀 Run Analysis")
        
        if submitted:
            try:
                with st.spinner("🔄 Running R analysis..."):
                    # Use the RMCP CLI to run the analysis
                    import subprocess
                    import json
                    
                    # Convert DataFrame to RMCP table format (dict with column arrays)
                    data_dict = {}
                    for col in data.columns:
                        data_dict[col] = data[col].tolist()
                    
                    # Prepare the MCP request
                    mcp_request = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": selected_tool_id,
                            "arguments": {
                                "data": data_dict,
                                **{k: v for k, v in params.items() if v != '' and v is not None}
                            }
                        }
                    }
                    
                    # Run RMCP via subprocess
                    process = subprocess.run([
                        'rmcp', 'start'
                    ], 
                    input=json.dumps(mcp_request),
                    text=True,
                    capture_output=True,
                    timeout=30
                    )
                    
                    if process.returncode == 0:
                        try:
                            # RMCP outputs logs to stderr and JSON result after "Server error:" in stderr
                            # Parse both stdout and stderr to find the JSON result
                            all_output = process.stdout + '\n' + process.stderr
                            
                            # Look for JSON result after "Server error:" or as standalone JSON
                            json_result = None
                            
                            # First try to find JSON after "Server error:"
                            if "Server error:" in all_output:
                                parts = all_output.split("Server error:")
                                if len(parts) > 1:
                                    potential_json = parts[-1].strip()
                                    if potential_json.startswith('{'):
                                        json_result = potential_json
                            
                            # If not found, look for any JSON line
                            if not json_result:
                                for line in all_output.split('\n'):
                                    line = line.strip()
                                    if line.startswith('{') and '"jsonrpc"' in line:
                                        json_result = line
                                        break
                            
                            if not json_result:
                                st.error("❌ No JSON result found in output")
                                st.code("STDOUT:\n" + process.stdout + "\n\nSTDERR:\n" + process.stderr)
                                return
                            
                            result = json.loads(json_result)
                            
                            st.subheader("📊 Results")
                            
                            if 'error' in result:
                                st.error(f"❌ Analysis failed: {result['error']}")
                            elif 'result' in result:
                                analysis_result = result['result']
                                
                                # RMCP returns results in 'content' array format
                                if 'content' in analysis_result:
                                    for content_item in analysis_result['content']:
                                        if content_item.get('type') == 'text':
                                            # Parse the text content (often contains JSON-like data)
                                            text_content = content_item['text']
                                            
                                            try:
                                                # Try to parse as Python dict/JSON
                                                import ast
                                                parsed_content = ast.literal_eval(text_content)
                                                
                                                if isinstance(parsed_content, dict):
                                                    # Display statistics nicely
                                                    if 'statistics' in parsed_content:
                                                        st.write("**📊 Summary Statistics:**")
                                                        stats_df = pd.DataFrame(parsed_content['statistics']).T
                                                        st.dataframe(stats_df)
                                                    
                                                    # Display other key-value pairs
                                                    for key, value in parsed_content.items():
                                                        if key != 'statistics':
                                                            st.write(f"**{key.title()}:** {value}")
                                                
                                                else:
                                                    st.code(text_content)
                                            
                                            except (ValueError, SyntaxError):
                                                # If not parseable, show as code
                                                st.code(text_content)
                                        
                                        elif content_item.get('type') == 'image':
                                            # Handle image content
                                            if 'data' in content_item:
                                                st.image(content_item['data'])
                                
                                else:
                                    # Fallback display
                                    st.json(analysis_result)
                            
                            else:
                                st.success("✅ Analysis completed successfully")
                                st.json(result)
                        
                        except json.JSONDecodeError:
                            st.error("❌ Could not parse analysis results")
                            st.code(process.stdout)
                    
                    else:
                        st.error(f"❌ Analysis failed: {process.stderr}")
                        
            except subprocess.TimeoutExpired:
                st.error("❌ Analysis timed out (>30 seconds)")
            except Exception as e:
                st.error(f"❌ Error running analysis: {e}")
            
            finally:
                # No cleanup needed since we're using in-memory data
                pass

else:
    st.info("👆 Please upload a CSV file to begin analysis")

# Claude AI Assistant
if client and data is not None:
    st.subheader("🤖 Claude AI Assistant")
    
    user_question = st.text_area(
        "Ask Claude about your data or analysis:",
        placeholder="e.g., 'What type of regression should I use for this data?' or 'How do I interpret these results?'"
    )
    
    if st.button("💬 Ask Claude") and user_question:
        try:
            with st.spinner("🤔 Claude is thinking..."):
                # Prepare context about the data
                data_context = f"""
                Dataset Info:
                - Shape: {data.shape[0]} rows, {data.shape[1]} columns
                - Columns: {', '.join(data.columns.tolist())}
                - Numeric columns: {', '.join(data.select_dtypes(include=['number']).columns.tolist())}
                - Missing values: {data.isnull().sum().sum()} total
                
                Available RMCP tools: {', '.join([tool for category in AVAILABLE_TOOLS.values() for tool in category.values()])}
                """
                
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=[{
                        "role": "user", 
                        "content": f"{data_context}\n\nUser question: {user_question}"
                    }]
                )
                
                st.write("**Claude's Response:**")
                st.write(message.content[0].text)
                
        except Exception as e:
            st.error(f"❌ Error communicating with Claude: {e}")

# Sample data
st.subheader("📚 Sample Data")
col1, col2 = st.columns(2)

with col1:
    if st.button("📊 Generate Sample Economic Data"):
        # Create sample economic dataset
        import numpy as np
        np.random.seed(42)
        
        n = 200
        sample_data = pd.DataFrame({
            'gdp_growth': np.random.normal(2.5, 1.2, n),
            'inflation': np.random.normal(3.0, 0.8, n),
            'unemployment': np.random.normal(5.5, 1.5, n),
            'interest_rate': np.random.normal(2.0, 0.5, n),
            'year': np.repeat(range(2000, 2020), 10),
            'country': np.tile(['USA', 'GER', 'JPN', 'UK', 'FRA', 'ITA', 'CAN', 'AUS', 'ESP', 'NLD'], 20)
        })
        
        # Add some relationships
        sample_data['gdp_growth'] = (
            2.5 - 0.3 * sample_data['unemployment'] + 
            0.2 * sample_data['inflation'] + 
            np.random.normal(0, 0.5, n)
        )
        
        temp_sample = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        sample_data.to_csv(temp_sample.name, index=False)
        
        st.success("✅ Sample economic data generated!")
        st.download_button(
            "📥 Download Sample Data",
            data=sample_data.to_csv(index=False),
            file_name="sample_economic_data.csv",
            mime="text/csv"
        )

with col2:
    if st.button("📈 Generate Time Series Data"):
        # Create sample time series
        import numpy as np
        from datetime import datetime, timedelta
        
        np.random.seed(123)
        dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
        
        # Simulated stock price with trend and seasonality
        trend = np.linspace(100, 150, len(dates))
        seasonal = 10 * np.sin(2 * np.pi * np.arange(len(dates)) / 365.25)
        noise = np.random.normal(0, 5, len(dates))
        price = trend + seasonal + noise
        
        ts_data = pd.DataFrame({
            'date': dates,
            'price': price,
            'volume': np.random.lognormal(10, 0.5, len(dates)),
            'returns': np.concatenate([[0], np.diff(np.log(price))])
        })
        
        st.success("✅ Sample time series data generated!")
        st.download_button(
            "📥 Download Time Series Data",
            data=ts_data.to_csv(index=False),
            file_name="sample_time_series.csv",
            mime="text/csv"
        )

# Footer
st.markdown("---")
st.markdown("""
**Getting Started:**
1. 🔑 Enter your Claude API key in the sidebar
2. 📁 Upload your CSV data file  
3. 🛠️ Select an analysis tool from the categories
4. ⚙️ Configure parameters and run analysis
5. 🤖 Ask Claude AI for help interpreting results

*Built with RMCP (R Model Context Protocol) - Advanced econometric analysis made simple*
""")