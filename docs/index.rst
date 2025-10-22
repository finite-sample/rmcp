RMCP Documentation
==================

**Statistical Analysis through Natural Conversation**

RMCP is a Model Context Protocol (MCP) server that provides comprehensive statistical analysis capabilities through R. With 53 statistical analysis tools across 11 categories, RMCP enables AI assistants to perform sophisticated statistical modeling, econometric analysis, machine learning, time series analysis, and data science tasks through natural conversation.

Features
--------

* **53 Statistical Tools** across 11 categories including regression, time series, machine learning, and visualization
* **Multiple Interfaces** - Python package (CLI) and HTTP server for different use cases
* **Natural Language Interface** - Convert plain English to statistical formulas and analyses
* **Professional Visualizations** - Inline plots and charts displayed directly in Claude conversations  
* **MCP Protocol Support** - Full compatibility with Claude Desktop and other MCP clients
* **Flexible R Integration** - Execute both structured tools and custom R code with security validation
* **Error Recovery** - Intelligent error diagnosis with suggested fixes

Choose Your Interface
---------------------

RMCP offers two ways to access statistical analysis capabilities:

📦 **Python Package** (``pip install rmcp``)
   Local installation for Claude Desktop integration

🌐 **HTTP Server** (Cloud deployment)
   Web API for applications and remote access

Getting Started
---------------

**Python Package:**
   1. ``pip install rmcp``
   2. ``rmcp start``
   3. Configure Claude Desktop

**HTTP Server:**
   Use our deployed server or deploy your own

Quick Links
-----------

**Package Documentation:**

* :doc:`package/user_guide/installation` - Installation and setup
* :doc:`package/user_guide/quick_start` - Usage examples and tutorials
* :doc:`package/api/modules` - Complete API reference

**HTTP Server Documentation:**

* :doc:`http-server/getting-started` - HTTP API usage guide
* :doc:`http-server/api-reference` - API endpoints and examples
* :doc:`http-server/deployment` - Deployment instructions

Documentation

.. toctree::
   :maxdepth: 2
   :caption: Python Package

   package/user_guide/installation
   package/user_guide/quick_start
   package/configuration/index
   troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: HTTP Server

   http-server/getting-started
   http-server/api-reference
   http-server/deployment

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   package/api/modules

.. toctree::
   :maxdepth: 2
   :caption: Shared Resources

   shared/examples
   shared/troubleshooting

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`