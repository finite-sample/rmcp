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
    # Regression tools
    "linear_model",
    "logistic_regression",
    "correlation_analysis",
    # Time series tools
    "arima_model",
    "decompose_timeseries",
    "stationarity_test",
    # Statistical tests
    "t_test",
    "anova",
    "chi_square_test",
    "normality_test",
    # Descriptive statistics
    "summary_stats",
    "outlier_detection",
    "frequency_table",
    # Econometrics
    "panel_regression",
    "instrumental_variables",
    "var_model",
    # Machine learning
    "kmeans_clustering",
    "decision_tree",
    "random_forest",
    # Visualization
    "scatter_plot",
    "histogram",
    "boxplot",
    "time_series_plot",
    "correlation_heatmap",
    "regression_plot",
    # Data transformations
    "lag_lead",
    "winsorize",
    "difference",
    "standardize",
    # File operations
    "read_csv",
    "read_excel",
    "read_json",
    "write_csv",
    "data_info",
    "filter_data",
    # Helper tools
    "suggest_fix",
    "validate_data",
    "load_example",
    # Formula building
    "build_formula",
    "validate_formula",
]
