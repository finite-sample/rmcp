Validated Working Examples
=========================

**Live Server**: https://rmcp-server-394229601724.us-central1.run.app

These examples have been tested against the live RMCP server and are guaranteed to work.

.. note::

   The MCP endpoint enforces ``MCP-Protocol-Version: 2025-11-25`` on every
   request. Using an older version string will result in a ``400`` response
   before the JSON-RPC body is processed.

Business Performance Analysis
-----------------------------

This example analyzes the relationship between sales performance and business metrics.

**Sample Dataset:**
- **Sales**: Monthly sales revenue ($)
- **Marketing Spend**: Monthly marketing budget ($)  
- **Customer Satisfaction**: Customer satisfaction scores (1-10)
- **Website Visits**: Monthly website visitors

Step 1: Initialize Session
~~~~~~~~~~~~~~~~~~~~~~~~~~

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
           "name": "business-analyst",
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
         "resources": {"subscribe": true, "listChanged": true},
         "prompts": {"listChanged": false},
         "logging": {},
         "completion": {}
       },
       "serverInfo": {
         "name": "RMCP MCP Server",
         "version": "0.7.0"
       }
     }
   }

⚠️ **Important**: Extract the ``MCP-Session-Id`` from response headers and use in subsequent requests.

Step 2: Linear Regression Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analyze how marketing spend and customer satisfaction impact sales.

.. code-block:: bash

   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
     -H "Content-Type: application/json" \
     -H "MCP-Protocol-Version: 2025-11-25" \
     -H "MCP-Session-Id: YOUR_SESSION_ID" \
     -d '{
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/call",
       "params": {
         "name": "linear_model",
         "arguments": {
           "formula": "sales ~ marketing_spend + customer_satisfaction",
           "data": {
             "sales": [15000, 18000, 12000, 22000, 16000, 20000, 14000, 25000, 13000, 19000],
             "marketing_spend": [2000, 2500, 1500, 3000, 2200, 2800, 1800, 3500, 1600, 2600],
             "customer_satisfaction": [8.5, 8.8, 7.2, 9.1, 8.0, 8.9, 7.8, 9.3, 7.5, 8.7]
           },
           "family": "gaussian"
         }
       }
     }'

**Actual Response (Verified):**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 2,
     "result": {
       "content": [
         {
           "type": "text",
           "text": "## Linear Regression Results\n\n**Model Statistics:**\n- R² = 0.995\n- Adjusted R² = 0.9935\n- F-statistic = 693.12 (p < 0.001)\n\n### Coefficients\n\n|term                  |  estimate| std.error| statistic| p.value|   conf.low|  conf.high|\n|:---------------------|---------:|---------:|---------:|-------:|----------:|----------:|\n|(Intercept)           | 4376.9072| 2752.7349|    1.5900|  0.1559| -2132.2766| 10886.0910|\n|marketing_spend       |    6.7903|    0.5045|   13.4608|  0.0000|     5.5975|     7.9832|\n|customer_satisfaction | -350.1367|  457.5716|   -0.7652|  0.4692| -1432.1216|   731.8481|",
           "annotations": {
             "mimeType": "text/markdown"
           }
         }
       ],
       "structuredContent": {
         "type": "json",
         "json": {
           "coefficients": {
             "(Intercept)": 4376.9072,
             "marketing_spend": 6.7903,
             "customer_satisfaction": -350.1367
           },
           "r_squared": 0.995,
           "adj_r_squared": 0.9935,
           "f_statistic": 693.1181,
           "f_p_value": 8.9899e-9
         }
       }
     }
   }

**Key Findings:**
- **Strong Model**: R² = 0.995 (explains 99.5% of sales variation)
- **Marketing ROI**: Every $1 in marketing generates $6.79 in sales
- **Customer Satisfaction**: Not statistically significant (p = 0.47)
- **Model Significance**: F-statistic = 693.12 (p < 0.001)

Step 3: Correlation Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Examine relationships between all business metrics.

.. code-block:: bash

   curl -X POST https://rmcp-server-394229601724.us-central1.run.app/mcp \
     -H "Content-Type: application/json" \
     -H "MCP-Protocol-Version: 2025-11-25" \
     -H "MCP-Session-Id: YOUR_SESSION_ID" \
     -d '{
       "jsonrpc": "2.0",
       "id": 3,
       "method": "tools/call",
       "params": {
         "name": "correlation_analysis",
         "arguments": {
           "data": {
             "sales": [15000, 18000, 12000, 22000, 16000, 20000, 14000, 25000, 13000, 19000],
             "marketing_spend": [2000, 2500, 1500, 3000, 2200, 2800, 1800, 3500, 1600, 2600],
             "customer_satisfaction": [8.5, 8.8, 7.2, 9.1, 8.0, 8.9, 7.8, 9.3, 7.5, 8.7],
             "website_visits": [1200, 1500, 900, 1800, 1300, 1700, 1100, 2000, 950, 1600]
           },
           "method": "pearson"
         }
       }
     }'

**Actual Response (Verified):**

.. code-block:: json

   {
     "jsonrpc": "2.0",
     "id": 3,
     "result": {
       "content": [
         {
           "type": "text",
           "text": "## Correlation Matrix\n\n|Variable              | sales| marketing_spend| customer_satisfaction| website_visits|\n|:---------------------|-----:|---------------:|---------------------:|--------------:|\n|sales                 | 1.000|           0.997|                 0.930|          0.992|\n|marketing_spend       | 0.997|           1.000|                 0.940|          0.996|\n|customer_satisfaction | 0.930|           0.940|                 1.000|          0.951|\n|website_visits        | 0.992|           0.996|                 0.951|          1.000|"
         }
       ],
       "structuredContent": {
         "type": "json",
         "json": {
           "correlation_matrix": {
             "sales": {
               "marketing_spend": 0.9973,
               "customer_satisfaction": 0.93,
               "website_visits": 0.9918
             }
           },
           "significance_tests": {
             "sales_marketing_spend": {
               "correlation": 0.9973,
               "p_value": 2.408e-10
             },
             "sales_customer_satisfaction": {
               "correlation": 0.93,
               "p_value": 0.0001
             }
           }
         }
       }
     }
   }

**Key Insights:**
- **Sales ↔ Marketing**: r = 0.997 (p < 0.001) - Very strong correlation
- **Sales ↔ Website Visits**: r = 0.992 (p < 0.001) - Very strong correlation  
- **Sales ↔ Customer Satisfaction**: r = 0.930 (p < 0.001) - Strong correlation
- **All relationships**: Statistically significant with p < 0.001

Python Client Implementation
----------------------------

Complete working Python client based on the validated examples:

.. code-block:: python

   import requests
   import json

   class RMCPBusinessAnalytics:
       def __init__(self):
           self.base_url = "https://rmcp-server-394229601724.us-central1.run.app"
           self.session = requests.Session()
           self.session_id = None
           
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
                       "clientInfo": {
                           "name": "business-analytics",
                           "version": "1.0"
                       }
                   }
               }
           )
           
           if response.ok:
               self.session_id = response.headers.get("Mcp-Session-Id")
               return response.json()
           else:
               raise Exception(f"Failed to initialize: {response.text}")
               
       def analyze_sales_performance(self, sales_data):
           """Analyze sales performance using linear regression"""
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
                       "name": "linear_model",
                       "arguments": {
                           "formula": "sales ~ marketing_spend + customer_satisfaction",
                           "data": sales_data,
                           "family": "gaussian"
                       }
                   }
               }
           )
           
           return response.json()
           
       def analyze_correlations(self, business_data):
           """Analyze correlations between business metrics"""
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
                   "id": 3,
                   "method": "tools/call",
                   "params": {
                       "name": "correlation_analysis",
                       "arguments": {
                           "data": business_data,
                           "method": "pearson"
                       }
                   }
               }
           )
           
           return response.json()

   # Usage Example
   if __name__ == "__main__":
       client = RMCPBusinessAnalytics()
       
       # Sample business data
       sales_data = {
           "sales": [15000, 18000, 12000, 22000, 16000, 20000, 14000, 25000, 13000, 19000],
           "marketing_spend": [2000, 2500, 1500, 3000, 2200, 2800, 1800, 3500, 1600, 2600],
           "customer_satisfaction": [8.5, 8.8, 7.2, 9.1, 8.0, 8.9, 7.8, 9.3, 7.5, 8.7]
       }
       
       business_data = {
           **sales_data,
           "website_visits": [1200, 1500, 900, 1800, 1300, 1700, 1100, 2000, 950, 1600]
       }
       
       # Perform analyses
       regression_results = client.analyze_sales_performance(sales_data)
       correlation_results = client.analyze_correlations(business_data)
       
       print("Regression Analysis:")
       print(json.dumps(regression_results, indent=2))
       
       print("\nCorrelation Analysis:")
       print(json.dumps(correlation_results, indent=2))

JavaScript Client Implementation
-------------------------------

.. code-block:: javascript

   class RMCPBusinessAnalytics {
       constructor() {
           this.baseUrl = 'https://rmcp-server-394229601724.us-central1.run.app';
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
                       clientInfo: {
                           name: 'business-analytics-js',
                           version: '1.0'
                       }
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
       
       async analyzeSalesPerformance(salesData) {
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
                       name: 'linear_model',
                       arguments: {
                           formula: 'sales ~ marketing_spend + customer_satisfaction',
                           data: salesData,
                           family: 'gaussian'
                       }
                   }
               })
           });
           
           return await response.json();
       }
       
       async analyzeCorrelations(businessData) {
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
                   id: 3,
                   method: 'tools/call',
                   params: {
                       name: 'correlation_analysis',
                       arguments: {
                           data: businessData,
                           method: 'pearson'
                       }
                   }
               })
           });
           
           return await response.json();
       }
   }

   // Usage Example
   async function runBusinessAnalysis() {
       const client = new RMCPBusinessAnalytics();
       
       const salesData = {
           sales: [15000, 18000, 12000, 22000, 16000, 20000, 14000, 25000, 13000, 19000],
           marketing_spend: [2000, 2500, 1500, 3000, 2200, 2800, 1800, 3500, 1600, 2600],
           customer_satisfaction: [8.5, 8.8, 7.2, 9.1, 8.0, 8.9, 7.8, 9.3, 7.5, 8.7]
       };
       
       const businessData = {
           ...salesData,
           website_visits: [1200, 1500, 900, 1800, 1300, 1700, 1100, 2000, 950, 1600]
       };
       
       try {
           const regressionResults = await client.analyzeSalesPerformance(salesData);
           const correlationResults = await client.analyzeCorrelations(businessData);
           
           console.log('Regression Analysis:', regressionResults);
           console.log('Correlation Analysis:', correlationResults);
       } catch (error) {
           console.error('Analysis failed:', error);
       }
   }

Common Patterns and Best Practices
----------------------------------

Session Management
~~~~~~~~~~~~~~~~~~

✅ **Always initialize sessions first**
✅ **Extract session ID from response headers**  
✅ **Include session ID in all subsequent requests**
✅ **Handle session expiration gracefully**

.. code-block:: python

   def ensure_session(self):
       if not self.session_id:
           self.initialize()
       # Add retry logic for expired sessions

Data Format Guidelines
~~~~~~~~~~~~~~~~~~~~~~

✅ **Use JSON objects for structured data**
✅ **Ensure consistent data types within arrays**
✅ **Include proper variable names**
✅ **Validate data before sending**

.. code-block:: json

   // Good: Consistent data structure
   {
     "sales": [15000, 18000, 12000],
     "marketing": [2000, 2500, 1500]
   }
   
   // Bad: Inconsistent types
   {
     "sales": [15000, "18000", null],
     "marketing": [2000, 2500, 1500]
   }

Error Handling
~~~~~~~~~~~~~~

✅ **Check HTTP response status**
✅ **Parse JSON-RPC error responses**
✅ **Implement retry logic for network issues**
✅ **Log errors with context**

.. code-block:: python

   def handle_response(self, response):
       if not response.ok:
           raise Exception(f"HTTP {response.status_code}: {response.text}")
           
       data = response.json()
       if 'error' in data:
           error = data['error']
           raise Exception(f"RMCP Error {error['code']}: {error['message']}")
           
       return data['result']

Performance Tips
~~~~~~~~~~~~~~~~

✅ **Reuse sessions for multiple operations**
✅ **Batch related analyses when possible**
✅ **Use appropriate timeout values**
✅ **Monitor response times**

Validation Results
------------------

**Test Date**: October 21, 2025
**Server Version**: RMCP MCP Server v0.7.0
**Test Environment**: Production deployment on Google Cloud Run

✅ **Session Initialization**: Working
✅ **Linear Regression**: Working (R² = 0.995)
✅ **Correlation Analysis**: Working (all correlations > 0.9)
✅ **JSON Response Format**: Valid
✅ **Error Handling**: Proper JSON-RPC errors
✅ **Session Management**: Headers working correctly

**Performance**:
- **Session Init**: ~200ms
- **Linear Regression**: ~3s (10 observations)
- **Correlation Analysis**: ~1.5s (4 variables)
- **Total Analysis Time**: ~5s for complete business analysis

Next Steps
----------

1. **Explore More Tools**: Use ``/docs`` to see all 44 available statistical tools
2. **Scale Analysis**: Try with larger datasets (up to 10,000 observations)
3. **Advanced Models**: Experiment with time series, machine learning tools
4. **Integration**: Build these examples into your applications
5. **Visualization**: Use plotting tools for data visualization

🔗 **Related Resources**:

- **Interactive API Docs**: https://rmcp-server-394229601724.us-central1.run.app/docs  
- **Complete Tool Reference**: :doc:`api-reference`
- **Python Package Equivalent**: :doc:`../shared/examples`
- **Troubleshooting**: :doc:`../shared/troubleshooting`