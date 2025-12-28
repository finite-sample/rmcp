"""
RMCP Tools Module
This module contains all statistical analysis tools for the RMCP MCP server.
Tools are organized by category and registered with the MCP server.
Categories:
- regression: Linear and logistic regression, correlation analysis
- timeseries: ARIMA, decomposition, stationarity testing
- statistical_tests: t-tests, ANOVA, chi-square, normality tests
- descriptive: Summary statistics, outlier detection, frequency tables
- econometrics: Panel regression, instrumental variables, VAR models
- machine_learning: Clustering, decision trees, random forest
- visualization: Plots, charts, diagnostic visualizations
- transforms: Data transformations, scaling, differencing
- fileops: File operations for CSV, Excel, JSON
- helpers: Formula building, error recovery, example datasets
- formula_builder: Natural language to R formula conversion
"""

__all__ = [
    # Tools are registered dynamically by the server through discovery system
    # No explicit imports needed - tools are loaded at runtime
]
