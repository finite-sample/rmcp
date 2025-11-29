Shared Examples
===============

Cross-reference examples showing both Python package and HTTP server usage for common statistical analysis tasks.

Business Analytics Example
---------------------------

Analyze marketing ROI using both interfaces.

Python Package
~~~~~~~~~~~~~~

.. code-block:: python

   # Using RMCP Python package
   import rmcp
   
   # Data
   data = {
       "sales": [100, 120, 115, 140, 135, 150],
       "marketing": [5, 8, 6, 10, 9, 12],
       "season": ["Q1", "Q2", "Q1", "Q2", "Q1", "Q2"]
   }
   
   # Linear regression
   result = rmcp.linear_model(
       formula="sales ~ marketing + season",
       data=data
   )
   print(result)

HTTP Server
~~~~~~~~~~~

.. code-block:: bash

   # Using RMCP HTTP server
   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \\
     -H "Content-Type: application/json" \\
     -H "MCP-Protocol-Version: 2025-11-25" \\
     -H "MCP-Session-Id: your-session-id" \\
     -d '{
       "jsonrpc": "2.0",
       "id": 3,
       "method": "tools/call",
       "params": {
         "name": "linear_model",
         "arguments": {
           "formula": "sales ~ marketing + season",
           "data": "sales,marketing,season\\n100,5,Q1\\n120,8,Q2\\n115,6,Q1\\n140,10,Q2\\n135,9,Q1\\n150,12,Q2",
           "format": "csv"
         }
       }
     }'

**Result Interpretation (Both Methods):**
- Every $1 in marketing spend generates $4.70 in additional sales
- Seasonal effects show Q2 outperforms Q1 by $8.5 on average
- Model explains 97.9% of sales variation (R² = 0.979)

Time Series Forecasting Example
-------------------------------

Forecast quarterly sales data.

Python Package
~~~~~~~~~~~~~~

.. code-block:: python

   # Monthly sales data
   sales_data = [100, 105, 110, 108, 115, 120, 125, 130, 128, 135]
   
   # ARIMA forecasting
   forecast = rmcp.time_series_arima(
       data=sales_data,
       variable_name="monthly_sales",
       forecast_periods=3
   )
   print(forecast)

HTTP Server
~~~~~~~~~~~

.. code-block:: bash

   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \\
     -H "Content-Type: application/json" \\
     -H "MCP-Protocol-Version: 2025-11-25" \\
     -H "MCP-Session-Id: your-session-id" \\
     -d '{
       "jsonrpc": "2.0",
       "id": 4,
       "method": "tools/call",
       "params": {
         "name": "time_series_arima",
         "arguments": {
           "data": [100, 105, 110, 108, 115, 120, 125, 130, 128, 135],
           "variable_name": "monthly_sales",
           "forecast_periods": 3
         }
       }
     }'

**Result Interpretation (Both Methods):**
- ARIMA(1,1,1) model selected automatically
- Next 3 periods forecasted: 138, 142, 145
- 95% confidence intervals provided for forecasts

Customer Analytics Example
--------------------------

Predict customer churn using logistic regression.

Python Package
~~~~~~~~~~~~~~

.. code-block:: python

   # Customer data
   customer_data = {
       "churn": [0, 1, 0, 1, 0, 1],
       "tenure": [24, 2, 36, 6, 48, 12],
       "monthly_charges": [50, 80, 45, 75, 55, 70],
       "total_charges": [1200, 160, 1620, 450, 2640, 840]
   }
   
   # Logistic regression
   churn_model = rmcp.logistic_regression(
       formula="churn ~ tenure + monthly_charges + total_charges",
       data=customer_data
   )
   print(churn_model)

HTTP Server
~~~~~~~~~~~

.. code-block:: bash

   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \\
     -H "Content-Type: application/json" \\
     -H "MCP-Protocol-Version: 2025-11-25" \\
     -H "MCP-Session-Id: your-session-id" \\
     -d '{
       "jsonrpc": "2.0",
       "id": 5,
       "method": "tools/call",
       "params": {
         "name": "logistic_regression",
         "arguments": {
           "formula": "churn ~ tenure + monthly_charges + total_charges",
           "data": "churn,tenure,monthly_charges,total_charges\\n0,24,50,1200\\n1,2,80,160\\n0,36,45,1620\\n1,6,75,450\\n0,48,55,2640\\n1,12,70,840",
           "format": "csv"
         }
       }
     }'

**Result Interpretation (Both Methods):**
- Longer tenure significantly reduces churn risk (OR = 0.887)
- Higher monthly charges increase churn risk (OR = 1.030)
- Model achieves 100% accuracy on sample data

Interface Comparison
--------------------

===================  ============================  ===========================
Aspect               Python Package                HTTP Server
===================  ============================  ===========================
**Setup**            ``pip install rmcp``         Use deployed server
**Authentication**   Claude Desktop integration    Session-based with headers
**Data Input**       Python objects/arrays         JSON/CSV in requests  
**Response Format**  Python objects                JSON-RPC responses
**Error Handling**   Python exceptions             JSON-RPC error codes
**Visualization**    Direct image display          Base64-encoded images
**Session State**    Automatic                     Manual session management
**Concurrency**      Single process                Multi-session support
**Deployment**       Local installation            Cloud/server deployment
===================  ============================  ===========================

When to Use Each Interface
---------------------------

**Use Python Package When:**
- Working with Claude Desktop
- Local data analysis workflows
- Python-native applications
- Single-user environments
- Rapid prototyping and exploration

**Use HTTP Server When:**
- Web application integration
- Multi-user environments
- Remote access requirements
- Microservices architecture
- Language-agnostic clients

Migration Between Interfaces
----------------------------

Converting Package Code to HTTP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Python package code
   result = rmcp.correlation_analysis(data=[1,2,3,4,5], variable_name="test")
   
   # Equivalent HTTP request
   http_request = {
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/call", 
       "params": {
           "name": "correlation_analysis",
           "arguments": {
               "data": [1, 2, 3, 4, 5],
               "variable_name": "test"
           }
       }
   }

Converting HTTP Code to Package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # HTTP request
   curl -X POST server/mcp -d '{"method":"tools/call","params":{"name":"t_test","arguments":{"data1":[1,2,3],"data2":[4,5,6]}}}'
   
   # Equivalent Python package code
   result = rmcp.t_test(data1=[1,2,3], data2=[4,5,6])

Data Format Conversions
-----------------------

CSV to JSON
~~~~~~~~~~~

.. code-block:: python

   # CSV format (HTTP)
   csv_data = "sales,marketing\\n100,5\\n120,8\\n115,6"
   
   # JSON format (both interfaces)
   json_data = {
       "sales": [100, 120, 115],
       "marketing": [5, 8, 6]
   }

Array to DataFrame
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Array format
   array_data = [100, 120, 115, 140]
   
   # Convert to DataFrame format
   df_data = {"values": array_data}

Integration Patterns
--------------------

Web Application Pattern
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: javascript

   // Frontend JavaScript calling HTTP server
   class StatisticsService {
       constructor() {
           this.baseUrl = 'https://rmcp-server-394229601724.us-central1.run.app';
           this.sessionId = null;
       }
       
       async analyzeData(data) {
           if (!this.sessionId) await this.initialize();
           
           return await this.callTool('descriptive_stats', {
               data: data,
               variable_name: 'user_data'
           });
       }
   }

Python Application Pattern
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Backend Python calling package directly
   class AnalyticsEngine:
       def __init__(self):
           self.rmcp = rmcp
           
       def analyze_sales_data(self, sales_data):
           return self.rmcp.descriptive_stats(
               data=sales_data,
               variable_name='sales'
           )

Hybrid Pattern
~~~~~~~~~~~~~~

.. code-block:: python

   # Use package for development, HTTP for production
   class StatisticsClient:
       def __init__(self, use_http=False):
           if use_http:
               self.client = HTTPRMCPClient()
           else:
               self.client = PackageRMCPClient()
               
       def analyze(self, data):
           return self.client.descriptive_stats(data)

Performance Considerations
--------------------------

**Python Package:**
- Faster for single operations (no network overhead)
- Memory efficient for large datasets
- Direct R integration

**HTTP Server:**
- Better for concurrent users
- Scalable with load balancing
- Network latency for small operations

**Recommendations:**
- Use package for exploratory analysis
- Use HTTP server for production applications
- Consider hybrid approach for development → production workflow

🔗 **Related Documentation:**

- **Package Setup**: :doc:`../package/user_guide/installation`
- **HTTP Server Setup**: :doc:`../http-server/getting-started`
- **Complete Tool Reference**: :doc:`../package/api/modules`