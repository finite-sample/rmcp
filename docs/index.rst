RMCP Documentation
==================

**Statistical Analysis through Natural Conversation**

RMCP is a Model Context Protocol (MCP) server that provides comprehensive statistical analysis capabilities through R. With 44 statistical analysis tools across 11 categories, RMCP enables AI assistants to perform sophisticated statistical modeling, econometric analysis, machine learning, time series analysis, and data science tasks through natural conversation.

Features
--------

* **44 Statistical Tools** across 11 categories including regression, time series, machine learning, and visualization
* **Natural Language Interface** - Convert plain English to statistical formulas and analyses
* **Professional Visualizations** - Inline plots and charts displayed directly in Claude conversations  
* **MCP Protocol Support** - Full compatibility with Claude Desktop and other MCP clients
* **Flexible R Integration** - Execute both structured tools and custom R code with security validation
* **Error Recovery** - Intelligent error diagnosis with suggested fixes

Getting Started
---------------

1. **Install**: ``pip install rmcp``
2. **Start**: ``rmcp start``
3. **Configure** your MCP client to connect to RMCP

Quick Links
-----------

* :doc:`user_guide/installation` - Installation and setup
* :doc:`user_guide/quick_start` - Usage examples and tutorials
* :doc:`api/modules` - Complete API reference

Documentation

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