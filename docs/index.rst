RMCP: R Model Context Protocol Server
=====================================

.. image:: https://github.com/finite-sample/rmcp/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/finite-sample/rmcp/actions/workflows/ci.yml
   :alt: Python application

.. image:: https://img.shields.io/pypi/v/rmcp.svg
   :target: https://pypi.org/project/rmcp/
   :alt: PyPI version

.. image:: https://pepy.tech/badge/rmcp
   :target: https://pepy.tech/project/rmcp
   :alt: Downloads

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License: MIT

.. image:: https://img.shields.io/badge/python-3.9+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python 3.9+

**Version 0.3.7** - A comprehensive Model Context Protocol (MCP) server with 40 statistical analysis tools across 9 categories. RMCP enables AI assistants and applications to perform sophisticated statistical modeling, econometric analysis, machine learning, time series analysis, and data science tasks seamlessly through natural conversation.

🎉 **Now with 40 statistical tools across 9 categories including natural language formula building and intelligent error recovery!**

Quick Start
-----------

Installation::

    pip install rmcp

Check R packages and start the server::

    # Check R packages are installed
    rmcp check-r-packages

    # Start the MCP server
    rmcp start

That's it! RMCP is now ready to handle statistical analysis requests via the Model Context Protocol.

Features
--------

📊 **Comprehensive Statistical Analysis (40 Tools)**

* **Regression & Correlation**: Linear regression, logistic regression, correlation analysis
* **Time Series Analysis**: ARIMA modeling, decomposition, stationarity testing  
* **Data Transformation**: Lag/lead variables, winsorization, differencing, standardization
* **Statistical Testing**: t-tests, ANOVA, chi-square tests, normality tests
* **Machine Learning**: K-means clustering, decision trees, random forest
* **Data Visualization**: Scatter plots, histograms, time series plots, correlation heatmaps
* **File Operations**: CSV, Excel, JSON import/export, data filtering
* **Natural Language & User Experience**: Formula builder, intelligent error recovery

📈 **Visual Analytics Revolution**

* **Inline Image Display**: All visualization tools display plots directly in Claude conversations
* **Base64 Encoding**: Professional-quality PNG images appear instantly
* **Multi-content MCP Responses**: Support for text + image content
* **Publication Quality**: ggplot2-styled visualizations ready for presentations

Documentation
=============

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/installation
   user_guide/quick_start
   troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`