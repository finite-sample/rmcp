HTTP Server Getting Started Guide
==================================

This guide shows you how to use RMCP's HTTP server for statistical analysis through web APIs.

Overview
--------

RMCP HTTP server provides the same statistical analysis capabilities as the Python package, but accessible via HTTP endpoints. This is ideal for:

- **Web applications** that need statistical analysis
- **Remote access** to statistical tools
- **Microservices** architectures
- **Multi-language** client support

🌐 **Live Server**: https://rmcp-server-394229601724.us-central1.run.app

Available Endpoints
-------------------

===================  =========  ===============================================
Endpoint             Method     Description
===================  =========  ===============================================
``/``                GET        Landing page with server information
``/mcp``             POST       Main MCP protocol endpoint
``/mcp/sse``         GET        Server-Sent Events for real-time updates  
``/health``          GET        Health check and server status
``/docs``            GET        Interactive Swagger UI documentation
``/redoc``           GET        Alternative ReDoc documentation
===================  =========  ===============================================

Quick Start
-----------

1. Initialize Session
~~~~~~~~~~~~~~~~~~~~~

All MCP communication requires session initialization:

.. note::

   The server enforces the ``2025-11-25`` protocol version. Initialization
   requests using a different ``protocolVersion`` are rejected, and every
   subsequent request must include the matching ``MCP-Protocol-Version``
   header.

.. code-block:: bash

   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
     -H "Content-Type: application/json" \
     -H "MCP-Protocol-Version: 2025-11-25" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "initialize",
       "params": {
         "protocolVersion": "2025-11-25",
         "capabilities": {},
         "clientInfo": {
           "name": "my-client",
           "version": "1.0"
         }
       }
     }'

**Response:**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 1,
     "result": {
       "protocolVersion": "2025-11-25",
       "capabilities": {
         "tools": {"listChanged": false},
         "resources": {"subscribe": true, "listChanged": true}
       },
       "serverInfo": {
         "name": "RMCP MCP Server",
         "version": "0.5.1"
       }
     }
   }

2. List Available Tools
~~~~~~~~~~~~~~~~~~~~~~~~

After initialization, list statistical analysis tools:

.. code-block:: bash

   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
     -H "Content-Type: application/json" \
     -H "MCP-Protocol-Version: 2025-11-25" \
     -H "MCP-Session-Id: your-session-id" \
     -d '{
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/list",
       "params": {}
     }'

This returns 53 statistical analysis tools including:

- ``linear_model`` - Linear and logistic regression
- ``correlation_analysis`` - Correlation matrices and testing
- ``time_series_arima`` - ARIMA modeling and forecasting
- ``descriptive_stats`` - Comprehensive descriptive statistics
- ``scatter_plot`` - Professional scatter plots

3. Execute Statistical Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Call statistical tools with your data:

.. code-block:: bash

   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
     -H "Content-Type: application/json" \
     -H "MCP-Protocol-Version: 2025-11-25" \
     -H "MCP-Session-Id: your-session-id" \
     -d '{
       "jsonrpc": "2.0",
       "id": 3,
       "method": "tools/call",
       "params": {
         "name": "correlation_analysis",
         "arguments": {
           "data": "sales,marketing\n100,5\n120,8\n115,6\n140,10",
           "format": "csv"
         }
       }
     }'

**Response:**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 3,
     "result": {
       "content": [
         {
           "type": "text",
           "text": "## Correlation Analysis Results\n\n**Correlation Coefficient:** r = 0.89\n**P-value:** p < 0.001\n**Interpretation:** Strong positive correlation between sales and marketing spend."
         }
       ]
     }
   }

Client Examples
---------------

Python Client
~~~~~~~~~~~~~~

.. code-block:: python

   import requests
   import json

   class RMCPClient:
       def __init__(self, base_url):
           self.base_url = base_url
           self.session_id = None
           self.session = requests.Session()
           
       def initialize(self):
           """Initialize MCP session"""
           response = self.session.post(
               f"{self.base_url}/mcp",
               headers={
                   "Content-Type": "application/json",
                   "MCP-Protocol-Version": "2025-11-25"
               },
               json={
                   "jsonrpc": "2.0",
                   "id": 1,
                   "method": "initialize",
                   "params": {
                       "protocolVersion": "2025-11-25",
                       "capabilities": {},
                       "clientInfo": {"name": "python-client", "version": "1.0"}
                   }
               }
           )
           
           if response.ok:
               self.session_id = response.headers.get("Mcp-Session-Id")
               return response.json()
           else:
               raise Exception(f"Failed to initialize: {response.text}")
               
       def call_tool(self, tool_name, arguments):
           """Call a statistical analysis tool"""
           if not self.session_id:
               self.initialize()
               
           response = self.session.post(
               f"{self.base_url}/mcp",
               headers={
                   "Content-Type": "application/json",
                   "MCP-Protocol-Version": "2025-11-25",
                   "MCP-Session-Id": self.session_id
               },
               json={
                   "jsonrpc": "2.0",
                   "id": 2,
                   "method": "tools/call",
                   "params": {
                       "name": tool_name,
                       "arguments": arguments
                   }
               }
           )
           
           return response.json()

   # Usage example
   client = RMCPClient("https://rmcp-server-394229601724.us-central1.run.app")
   result = client.call_tool("descriptive_stats", {
       "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
       "variable_name": "test_data"
   })
   print(result)

JavaScript Client
~~~~~~~~~~~~~~~~~~

.. code-block:: javascript

   class RMCPClient {
       constructor(baseUrl) {
           this.baseUrl = baseUrl;
           this.sessionId = null;
       }
       
       async initialize() {
           const response = await fetch(`${this.baseUrl}/mcp`, {
               method: 'POST',
               headers: {
                   'Content-Type': 'application/json',
                   'MCP-Protocol-Version': '2025-11-25'
               },
               body: JSON.stringify({
                   jsonrpc: '2.0',
                   id: 1,
                   method: 'initialize',
                   params: {
                       protocolVersion: '2025-11-25',
                       capabilities: {},
                       clientInfo: { name: 'js-client', version: '1.0' }
                   }
               })
           });
           
           if (response.ok) {
               this.sessionId = response.headers.get('Mcp-Session-Id');
               return await response.json();
           } else {
               throw new Error(`Failed to initialize: ${await response.text()}`);
           }
       }
       
       async callTool(toolName, arguments) {
           if (!this.sessionId) {
               await this.initialize();
           }
           
           const response = await fetch(`${this.baseUrl}/mcp`, {
               method: 'POST',
               headers: {
                   'Content-Type': 'application/json',
                   'MCP-Protocol-Version': '2025-11-25',
                   'MCP-Session-Id': this.sessionId
               },
               body: JSON.stringify({
                   jsonrpc: '2.0',
                   id: 2,
                   method: 'tools/call',
                   params: {
                       name: toolName,
                       arguments: arguments
                   }
               })
           });
           
           return await response.json();
       }
   }

   // Usage example
   const client = new RMCPClient('https://rmcp-server-394229601724.us-central1.run.app');
   
   client.callTool('linear_model', {
       formula: 'sales ~ marketing',
       data: 'sales,marketing\\n100,5\\n120,8\\n115,6\\n140,10',
       format: 'csv'
   }).then(result => {
       console.log(result);
   });

Real-time Updates with Server-Sent Events
------------------------------------------

For long-running statistical operations, monitor progress with SSE:

.. code-block:: javascript

   const eventSource = new EventSource(
       'https://rmcp-server-394229601724.us-central1.run.app/mcp/sse'
   );
   
   eventSource.onmessage = function(event) {
       const data = JSON.parse(event.data);
       
       if (event.type === 'notification') {
           console.log('Progress update:', data);
       } else if (event.type === 'keepalive') {
           console.log('Connection active');
       }
   };

Common Use Cases
----------------

Business Analytics
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Analyze marketing ROI
   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
     -H "Content-Type: application/json" \
     -H "MCP-Protocol-Version: 2025-11-25" \
     -H "MCP-Session-Id: your-session-id" \
     -d '{
       "jsonrpc": "2.0",
       "id": 3,
       "method": "tools/call",
       "params": {
         "name": "linear_model",
         "arguments": {
           "formula": "sales ~ marketing_spend + season",
           "data": "sales,marketing_spend,season\n100,5,Q1\n120,8,Q2\n115,6,Q1\n140,10,Q2",
           "format": "csv"
         }
       }
     }'

Time Series Forecasting
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Forecast future values
   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
     -H "Content-Type: application/json" \
     -H "MCP-Protocol-Version: 2025-11-25" \
     -H "MCP-Session-Id: your-session-id" \
     -d '{
       "jsonrpc": "2.0",
       "id": 4,
       "method": "tools/call",
       "params": {
         "name": "time_series_arima",
         "arguments": {
           "data": [100, 105, 110, 108, 115, 120, 125, 130],
           "variable_name": "monthly_sales",
           "forecast_periods": 3
         }
       }
     }'

Customer Analytics
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Predict customer churn
   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
     -H "Content-Type: application/json" \
     -H "MCP-Protocol-Version: 2025-11-25" \
     -H "MCP-Session-Id: your-session-id" \
     -d '{
       "jsonrpc": "2.0",
       "id": 5,
       "method": "tools/call",
       "params": {
         "name": "logistic_regression",
         "arguments": {
           "formula": "churn ~ tenure + monthly_charges + total_charges",
           "data": "churn,tenure,monthly_charges,total_charges\n0,24,50,1200\n1,2,80,160\n0,36,45,1620\n1,6,75,450",
           "format": "csv"
         }
       }
     }'

Error Handling
--------------

The server returns standard JSON-RPC 2.0 error responses:

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 1,
     "error": {
       "code": -32603,
       "message": "Session not initialized. Send initialize request first.",
       "data": {"type": "HTTPException"}
     }
   }

Common error codes:

- ``-32600``: Invalid Request
- ``-32603``: Internal Error  
- ``400``: Missing MCP headers
- ``405``: Method not allowed

Troubleshooting
---------------

**Q: Getting "Session not initialized" error?**

A: Always send an ``initialize`` request first and include the returned session ID in subsequent requests.

**Q: Missing MCP-Protocol-Version header error?**

A: All requests after initialization must include ``MCP-Protocol-Version: 2025-11-25`` header.

**Q: CORS errors in browser?**

A: The server supports CORS for web applications. Ensure you're including proper headers.

**Q: Connection timeout on SSE?**

A: SSE connections send keep-alive messages every 0.5 seconds. Check your firewall/proxy settings.

Next Steps
----------

- **Explore Tools**: Use ``/docs`` for interactive API exploration
- **Integration**: Build statistical analysis into your applications
- **Advanced Usage**: Check :doc:`api-reference` for complete tool documentation
- **Deployment**: See :doc:`deployment` for running your own server

🔗 **Links:**
- **Interactive Docs**: https://rmcp-server-394229601724.us-central1.run.app/docs
- **GitHub Repository**: https://github.com/finite-sample/rmcp
- **Python Package**: :doc:`../package/user_guide/quick_start`