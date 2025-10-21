HTTP Server API Reference
=========================

Complete reference for RMCP HTTP server endpoints and statistical tools.

🌐 **Live Server**: https://rmcp-server-394229601724.us-central1.run.app

🔍 **Interactive Docs**: https://rmcp-server-394229601724.us-central1.run.app/docs

Core Endpoints
--------------

Root Endpoint
~~~~~~~~~~~~~

.. http:get:: /

   Server landing page with information and navigation links.

   **Response**: HTML page with server status, documentation links, and quick start examples.

MCP Protocol Endpoint  
~~~~~~~~~~~~~~~~~~~~~~

.. http:post:: /mcp

   Main Model Context Protocol communication endpoint.

   **Request Headers:**
   
   - ``Content-Type: application/json``
   - ``MCP-Protocol-Version: 2025-06-18`` *(required after initialization)*
   - ``MCP-Session-Id: <session-id>`` *(included automatically after initialization)*

   **JSON-RPC 2.0 Request Body:**

   .. code-block:: json

      {
        "jsonrpc": "2.0", 
        "id": 1,
        "method": "<method_name>",
        "params": { ... }
      }

   **Available Methods:**

   ==================  ===============================================
   Method              Description
   ==================  ===============================================
   ``initialize``      Initialize MCP session
   ``tools/list``      List available statistical analysis tools
   ``tools/call``      Execute statistical analysis tool
   ``resources/list``  List available data resources
   ``prompts/list``    List available prompt templates
   ==================  ===============================================

Server-Sent Events
~~~~~~~~~~~~~~~~~~~

.. http:get:: /mcp/sse

   Real-time event stream for progress updates and notifications.

   **Response**: ``text/event-stream`` with JSON-encoded events:

   .. code-block:: javascript

      // Progress notification
      event: notification
      data: {"method": "notifications/progress", "params": {"progressToken": "abc", "progress": 50, "total": 100}}

      // Keep-alive signal  
      event: keepalive
      data: {"status": "ok"}

Health Check
~~~~~~~~~~~~

.. http:get:: /health

   Server health and status information.

   **Response:**

   .. code-block:: json

      {
        "status": "healthy",
        "transport": "HTTP"
      }

Session Management
------------------

All MCP communication requires session initialization and proper header management.

Initialize Session
~~~~~~~~~~~~~~~~~~

**Request:**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 1, 
     "method": "initialize",
     "params": {
       "protocolVersion": "2025-06-18",
       "capabilities": {},
       "clientInfo": {
         "name": "my-client",
         "version": "1.0"
       }
     }
   }

**Response:**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 1,
     "result": {
       "protocolVersion": "2025-06-18", 
       "capabilities": {
         "tools": {"listChanged": false},
         "resources": {"subscribe": true, "listChanged": true},
         "prompts": {"listChanged": false},
         "logging": {},
         "completion": {}
       },
       "serverInfo": {
         "name": "RMCP MCP Server",
         "version": "0.5.1"
       }
     }
   }

**Response Headers:**
- ``Mcp-Session-Id: <generated-session-id>`` - Use in subsequent requests

Statistical Analysis Tools
---------------------------

List Tools
~~~~~~~~~~

**Request:**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 2,
     "method": "tools/list", 
     "params": {}
   }

**Response:** List of 53 statistical analysis tools across 11 categories.

Call Tools
~~~~~~~~~~

**Request:**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 3,
     "method": "tools/call",
     "params": {
       "name": "<tool_name>",
       "arguments": { ... }
     }
   }

**Response:**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 3,
     "result": {
       "content": [
         {
           "type": "text",
           "text": "Statistical analysis results..."
         },
         {
           "type": "image",
           "data": "base64-encoded-image",
           "mimeType": "image/png"
         }
       ]
     }
   }

Regression Analysis Tools
~~~~~~~~~~~~~~~~~~~~~~~~~

linear_model
^^^^^^^^^^^^

Linear and logistic regression analysis with comprehensive diagnostics.

**Arguments:**

===================  ========  ===============================================
Parameter            Type      Description
===================  ========  ===============================================
``formula``          string    R formula (e.g., "y ~ x1 + x2")
``data``             string    Data in CSV format or array
``format``           string    Data format: "csv", "json", or "array" 
``family``           string    "gaussian" (linear) or "binomial" (logistic)
``include_plots``    boolean   Generate diagnostic plots (default: true)
===================  ========  ===============================================

**Example:**

.. code-block:: json

   {
     "name": "linear_model",
     "arguments": {
       "formula": "sales ~ marketing + season",
       "data": "sales,marketing,season\n100,5,1\n120,8,2\n115,6,1\n140,10,2",
       "format": "csv",
       "family": "gaussian"
     }
   }

**Returns:** Model summary, coefficients, R², diagnostics, and residual plots.

correlation_analysis  
^^^^^^^^^^^^^^^^^^^^

Correlation matrices with significance testing and confidence intervals.

**Arguments:**

===================  ========  ===============================================
Parameter            Type      Description
===================  ========  =============================================== 
``data``             mixed     Data in CSV format or numeric arrays
``format``           string    Data format: "csv", "json", or "array"
``method``           string    "pearson", "spearman", or "kendall"
``confidence_level`` number    Confidence level (default: 0.95)
``include_plots``    boolean   Generate correlation heatmap (default: true)
===================  ========  ===============================================

**Example:**

.. code-block:: json

   {
     "name": "correlation_analysis", 
     "arguments": {
       "data": {
         "sales": [100, 120, 115, 140],
         "marketing": [5, 8, 6, 10],
         "satisfaction": [7.5, 8.2, 7.8, 8.9]
       },
       "format": "json",
       "method": "pearson"
     }
   }

**Returns:** Correlation matrix, p-values, confidence intervals, and heatmap.

Time Series Analysis Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~

time_series_arima
^^^^^^^^^^^^^^^^^

ARIMA modeling with automatic order selection and forecasting.

**Arguments:**

===================  ========  ===============================================
Parameter            Type      Description
===================  ========  ===============================================
``data``             array     Time series values
``variable_name``    string    Name for the time series variable
``forecast_periods`` number    Number of periods to forecast
``auto_arima``       boolean   Use automatic order selection (default: true)
``seasonal``         boolean   Include seasonal components (default: false)
===================  ========  ===============================================

**Example:**

.. code-block:: json

   {
     "name": "time_series_arima",
     "arguments": {
       "data": [100, 105, 110, 108, 115, 120, 125, 130, 128, 135],
       "variable_name": "monthly_sales", 
       "forecast_periods": 3,
       "auto_arima": true
     }
   }

**Returns:** ARIMA model summary, forecasts with confidence intervals, and diagnostic plots.

Statistical Testing Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~

t_test
^^^^^^

One-sample, two-sample, and paired t-tests with effect sizes.

**Arguments:**

===================  ========  ===============================================
Parameter            Type      Description
===================  ========  ===============================================
``data1``            array     First data group
``data2``            array     Second data group (optional)
``test_type``        string    "one_sample", "two_sample", or "paired"
``mu``               number    Null hypothesis mean (for one-sample)
``confidence_level`` number    Confidence level (default: 0.95)
``alternative``      string    "two_sided", "less", or "greater"
===================  ========  ===============================================

**Example:**

.. code-block:: json

   {
     "name": "t_test",
     "arguments": {
       "data1": [23, 25, 27, 24, 26, 28, 25, 24],
       "data2": [20, 22, 24, 21, 23, 25, 22, 21],
       "test_type": "two_sample",
       "alternative": "two_sided"
     }
   }

**Returns:** T-statistic, p-value, confidence interval, and effect size.

Machine Learning Tools
~~~~~~~~~~~~~~~~~~~~~~~

kmeans_clustering
^^^^^^^^^^^^^^^^^

K-means clustering with optimal cluster selection and visualization.

**Arguments:**

===================  ========  ===============================================
Parameter            Type      Description
===================  ========  ===============================================
``data``             mixed     Data matrix in CSV format or arrays
``format``           string    Data format: "csv", "json", or "array"
``k``                number    Number of clusters (optional - auto-selects)
``max_k``            number    Maximum clusters to test (default: 10)
``include_plots``    boolean   Generate cluster visualization (default: true)
===================  ========  ===============================================

**Example:**

.. code-block:: json

   {
     "name": "kmeans_clustering",
     "arguments": {
       "data": "x,y\n1,2\n2,3\n8,9\n9,8\n1,1\n9,9",
       "format": "csv",
       "k": 2
     }
   }

**Returns:** Cluster assignments, centroids, within-cluster sum of squares, and visualization.

Data Analysis Tools
~~~~~~~~~~~~~~~~~~~

descriptive_stats
^^^^^^^^^^^^^^^^^

Comprehensive descriptive statistics with distribution analysis.

**Arguments:**

===================  ========  ===============================================
Parameter            Type      Description
===================  ========  ===============================================
``data``             array     Numeric data values
``variable_name``    string    Name for the variable
``include_plots``    boolean   Generate histogram and boxplot (default: true)
``confidence_level`` number    Confidence level for mean CI (default: 0.95)
===================  ========  ===============================================

**Example:**

.. code-block:: json

   {
     "name": "descriptive_stats",
     "arguments": {
       "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
       "variable_name": "test_scores",
       "include_plots": true
     }
   }

**Returns:** Mean, median, standard deviation, quartiles, skewness, kurtosis, and plots.

Visualization Tools
~~~~~~~~~~~~~~~~~~~

scatter_plot
^^^^^^^^^^^^

Professional scatter plots with trend lines and statistical annotations.

**Arguments:**

===================  ========  ===============================================
Parameter            Type      Description
===================  ========  ===============================================
``x``                array     X-axis values
``y``                array     Y-axis values  
``x_name``           string    X-axis label
``y_name``           string    Y-axis label
``add_trend_line``   boolean   Add linear trend line (default: true)
``add_confidence``   boolean   Add confidence bands (default: true)
``color_by``         array     Optional grouping variable
===================  ========  ===============================================

**Example:**

.. code-block:: json

   {
     "name": "scatter_plot",
     "arguments": {
       "x": [1, 2, 3, 4, 5],
       "y": [2, 4, 6, 8, 10],
       "x_name": "Marketing Spend",
       "y_name": "Sales Revenue", 
       "add_trend_line": true
     }
   }

**Returns:** Professional scatter plot with correlation statistics.

Error Handling
--------------

JSON-RPC 2.0 Error Codes
~~~~~~~~~~~~~~~~~~~~~~~~~

Standard JSON-RPC error responses:

==========  ===============================================
Code        Description
==========  ===============================================
``-32700``  Parse error - Invalid JSON
``-32600``  Invalid Request - JSON-RPC format error
``-32601``  Method not found - Unknown method
``-32602``  Invalid params - Parameter validation error
``-32603``  Internal error - Server processing error
==========  ===============================================

HTTP Error Codes
~~~~~~~~~~~~~~~~~

HTTP-specific errors:

==========  ===============================================
Code        Description
==========  ===============================================
``400``     Bad Request - Missing headers/invalid format
``405``     Method Not Allowed - Wrong HTTP method
``500``     Internal Server Error - Unexpected error
==========  ===============================================

Example Error Response
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 1,
     "error": {
       "code": -32603,
       "message": "400: Session not initialized. Send initialize request first.",
       "data": {"type": "HTTPException"}
     }
   }

Rate Limiting
-------------

The server implements reasonable rate limiting for stability:

- **Concurrent Sessions**: 100 active sessions
- **Request Rate**: 60 requests per minute per session
- **Tool Execution**: 10 concurrent tool executions per session

Exceeding limits returns HTTP 429 (Too Many Requests).

Security
--------

**Protocol Security:**
- MCP protocol version validation
- Session-based access control  
- Request origin validation

**Data Security:**
- R code execution in sandboxed environment
- File system access restrictions
- Package installation approval system

**Transport Security:**
- HTTPS encryption for data in transit
- CORS policy for browser access
- Standard HTTP security headers

Best Practices
--------------

Client Implementation
~~~~~~~~~~~~~~~~~~~~~

1. **Session Management**: Always initialize sessions and handle session IDs properly
2. **Error Handling**: Implement robust error handling for network and protocol errors
3. **Timeout Handling**: Set appropriate timeouts for long-running statistical operations
4. **Connection Pooling**: Reuse HTTP connections for better performance

Data Formats
~~~~~~~~~~~~

1. **CSV Format**: Best for tabular data with headers
2. **JSON Format**: Best for structured data with mixed types
3. **Array Format**: Best for simple numeric vectors

Performance Tips
~~~~~~~~~~~~~~~~

1. **Batch Operations**: Group related analysis calls when possible
2. **Data Size**: Keep datasets reasonable (<10MB) for optimal performance  
3. **Visualization**: Disable plots for large batch operations if not needed
4. **SSE Monitoring**: Use Server-Sent Events for long-running operations

Integration Examples
--------------------

See :doc:`getting-started` for complete client implementation examples in:

- Python with ``requests`` library
- JavaScript with ``fetch`` API  
- curl command-line examples

🔗 **Additional Resources:**

- **Interactive API Explorer**: https://rmcp-server-394229601724.us-central1.run.app/docs
- **ReDoc Documentation**: https://rmcp-server-394229601724.us-central1.run.app/redoc
- **GitHub Repository**: https://github.com/finite-sample/rmcp
- **Python Package Docs**: :doc:`../package/user_guide/quick_start`