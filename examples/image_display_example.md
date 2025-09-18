# RMCP Visual Analytics Example

**New in v0.3.7**: This example demonstrates how RMCP now displays professional-quality plots and visualizations directly in Claude conversations, revolutionizing data analysis workflows.

## 🎯 Revolutionary Visual Analytics

### Direct Image Display in Claude

RMCP visualization tools now return both comprehensive statistical analysis **and** publication-quality images directly in Claude:

```markdown
# When you ask Claude:
"Create a correlation heatmap of my sales, marketing, and customer satisfaction data"

# RMCP responds with:
# 1. 📊 Interactive heatmap displayed inline with color-coded correlation strengths
# 2. 📋 Statistical analysis: correlation matrix with exact values and significance tests  
# 3. 💡 Insights: "Strong positive correlation (r=0.89) between marketing and sales"
# 4. 🎨 Professional ggplot2 styling ready for presentations
```

### 🎨 Enhanced Visualization Tools (All 6 Support Inline Display)

**🔥 correlation_heatmap**: Color-coded correlation matrices with statistical significance testing
- Perfect for: Exploring relationships between multiple variables
- Visual: Color intensity shows correlation strength (-1 to +1)
- Analysis: p-values, confidence intervals, sample sizes

**📈 scatter_plot**: Interactive scatter plots with trend lines and grouping  
- Perfect for: Regression analysis, outlier detection, group comparisons
- Visual: Points, trend lines, confidence bands, group colors
- Analysis: Correlation coefficients, R², regression equations

**📊 histogram**: Distribution analysis with density overlays
- Perfect for: Understanding data distributions, checking normality
- Visual: Bars with density curves, group overlays
- Analysis: Mean, median, skewness, kurtosis statistics

**📦 boxplot**: Quartile analysis with outlier detection
- Perfect for: Comparing distributions, finding outliers
- Visual: Boxes, whiskers, outlier points, group comparisons  
- Analysis: Quartiles, IQR, outlier counts, group statistics

**⏱️ time_series_plot**: Temporal analysis with trend forecasting
- Perfect for: Time series analysis, trend identification
- Visual: Lines, points, smooth trends, confidence bands
- Analysis: Trend statistics, seasonal patterns, forecasts

**🔍 regression_plot**: Comprehensive diagnostic plots (4-panel)
- Perfect for: Model validation, assumption checking
- Visual: Residuals vs fitted, Q-Q plots, scale-location, leverage
- Analysis: Model diagnostics, outliers, influential points

### Usage Examples

#### 1. Correlation Heatmap (no file needed)

```json
{
  "tool": "correlation_heatmap",
  "arguments": {
    "data": {
      "sales": [100, 150, 200, 250, 300],
      "marketing": [10, 15, 25, 30, 40],
      "temperature": [20, 25, 30, 35, 40]
    },
    "method": "pearson",
    "title": "Sales Correlation Analysis"
  }
}
```

**Returns:**
- **Text**: Correlation matrix with values, statistics
- **Image**: Color-coded heatmap displayed directly in Claude

#### 2. Scatter Plot with Grouping

```json
{
  "tool": "scatter_plot", 
  "arguments": {
    "data": {
      "x": [1, 2, 3, 4, 5, 6, 7, 8],
      "y": [2, 4, 3, 6, 5, 8, 7, 10],
      "group": ["A", "A", "B", "B", "A", "A", "B", "B"]
    },
    "x": "x",
    "y": "y", 
    "group": "group",
    "title": "Sales vs Marketing by Region"
  }
}
```

**Returns:**
- **Text**: Correlation coefficient, data points count
- **Image**: Scatter plot with color-coded groups and trend lines

### Optional File Saving

You can still save plots to files if needed:

```json
{
  "tool": "correlation_heatmap",
  "arguments": {
    "data": {...},
    "file_path": "/path/to/save/heatmap.png",
    "return_image": true
  }
}
```

This saves the plot to a file **and** displays it inline in Claude.

### Technical Details

#### Image Format
- **Format**: PNG images with white background
- **Encoding**: Base64 for transmission
- **Resolution**: Configurable (default 800x600 pixels)
- **Quality**: 100 DPI for crisp display

#### MCP Content Response
Tools now return multiple content types:

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"correlation_matrix\": [[1.0, 0.95], [0.95, 1.0]], ...}"
    },
    {
      "type": "image", 
      "data": "iVBORw0KGgoAAAANSUhEUgAAA...",
      "mimeType": "image/png"
    }
  ]
}
```

#### Configuration Options

All visualization tools support these parameters:

```json
{
  "return_image": true,     // Enable/disable inline images (default: true)
  "file_path": "plot.png",  // Optional: also save to file
  "width": 800,             // Image width in pixels
  "height": 600             // Image height in pixels
}
```

### Benefits

1. **Immediate Visual Feedback**: See plots instantly without file management
2. **Streamlined Workflow**: Analysis and visualization in one conversation
3. **Better Context**: Images appear alongside statistical results
4. **No File Management**: No need to handle file paths or external viewers
5. **Responsive**: Works in any environment where Claude runs

### Backward Compatibility

- **Existing scripts**: All existing RMCP scripts continue to work unchanged
- **File paths**: Still supported for users who want to save plots
- **API**: No breaking changes to tool interfaces

This enhancement makes RMCP visualizations much more accessible and user-friendly, providing immediate visual feedback for statistical analyses directly within your Claude conversation.