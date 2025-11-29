# RMCP Streamlit Cloud Demo

An interactive web interface demonstrating RMCP's econometric capabilities with Claude AI integration.

## 🌐 Live Demo

**🚀 Try it now:** [RMCP on Streamlit Cloud](https://your-app-url.streamlit.app)

## 🔧 Local Development

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the App:**
   ```bash
   streamlit run app.py
   ```

3. **Open in Browser:**
   - Navigate to http://localhost:8501

## ☁️ Deploy to Streamlit Community Cloud

1. **Fork this repository**
2. **Connect to Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub account
   - Select this repository
   - Set main file path: `streamlit/app.py`
3. **Deploy!**

## 🔧 Setup

### Claude API Key
1. Get your API key from [Claude Console](https://console.anthropic.com/)
2. Enter it in the sidebar when the app starts
3. The key is stored only for your session (not saved)

### Data Upload
- Upload CSV files with your data
- The app will show a preview and data information
- All analyses work with your uploaded data

## 📊 Available Tools

### 📈 Descriptive Statistics
- **Summary Statistics**: Mean, median, mode, variance, etc.
- **Correlation Analysis**: Pearson and Spearman correlations
- **Outlier Detection**: Identify and analyze outliers

### 📊 Regression Analysis
- **Linear Regression**: Simple and multiple regression
- **Logistic Regression**: Binary outcome modeling
- **Panel Regression**: Fixed effects, random effects

### 🧪 Statistical Tests
- **T-Tests**: One-sample, two-sample, paired
- **Chi-Square Tests**: Independence testing
- **Normality Tests**: Shapiro-Wilk, Kolmogorov-Smirnov
- **Stationarity Tests**: Augmented Dickey-Fuller

### 📉 Time Series Analysis
- **ARIMA Models**: Autoregressive integrated moving average
- **VAR Models**: Vector autoregression
- **Forecasting**: Time series predictions
- **Cointegration Tests**: Long-run relationships

### 🔄 Data Transformations
- **Lag Variables**: Create lagged versions
- **Difference Variables**: First/second differences
- **Winsorization**: Outlier treatment
- **Standardization**: Z-score, min-max scaling

### 📊 Visualizations
- **Scatter Plots**: With trend lines and grouping
- **Time Series Plots**: Multiple variables over time
- **Histograms**: Distribution analysis
- **Correlation Heatmaps**: Visual correlation matrices

### 🎯 Advanced Econometrics
- **Instrumental Variables**: 2SLS estimation
- **Panel Fixed Effects**: Within-group estimation
- **Difference-in-Differences**: Causal inference
- **Regression Discontinuity**: Threshold effects

### 🤖 Machine Learning
- **Random Forest**: Ensemble modeling
- **Decision Trees**: Classification and regression
- **Clustering**: K-means, hierarchical
- **PCA Analysis**: Dimensionality reduction

## 🤖 Claude AI Assistant

The built-in Claude AI assistant can help you:
- Choose appropriate statistical methods
- Interpret analysis results
- Suggest next steps in your research
- Explain complex statistical concepts

Simply ask questions like:
- "What regression method should I use for this data?"
- "How do I interpret these coefficients?"
- "What does this p-value mean?"

## 📁 Example Data

The app works with any CSV file. Your data should have:
- Column headers in the first row
- Numeric variables for quantitative analysis
- Categorical variables for grouping/factors
- Time variables in standard formats (for time series)

## 🔒 Privacy & Security

- All analysis runs locally with your R installation
- Data is processed temporarily and not stored
- Claude API key is session-only (not saved)
- Uploaded files are automatically cleaned up

## 🛠️ Technical Details

- **Backend**: R statistical computing via subprocess
- **Frontend**: Streamlit web interface
- **AI Integration**: Anthropic Claude API
- **Data Processing**: Pandas DataFrames
- **Visualization**: R ggplot2 + Plotly integration

## 📞 Support

- Check the troubleshooting guide in `docs/troubleshooting.md`
- Report issues on GitHub
- Consult R documentation for statistical methods

## 🎯 Use Cases

Perfect for:
- **Academic Research**: Econometric analysis for papers
- **Business Analytics**: Market research and forecasting
- **Policy Analysis**: Causal inference and impact evaluation
- **Financial Modeling**: Risk analysis and portfolio optimization
- **Data Science**: Exploratory analysis and feature engineering

---

*Powered by RMCP (R Model Context Protocol) - Making advanced econometrics accessible to everyone.*
