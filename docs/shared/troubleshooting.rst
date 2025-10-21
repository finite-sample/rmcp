Shared Troubleshooting Guide
============================

Common issues and solutions for both Python package and HTTP server deployments.

Connection Issues
-----------------

MCP Protocol Errors
~~~~~~~~~~~~~~~~~~~~

**Problem**: "Missing required MCP-Protocol-Version header"

**Solution**: Include the protocol version header in HTTP requests:

.. code-block:: bash

   # Add this header to all requests after initialization
   -H "MCP-Protocol-Version: 2025-06-18"

**Problem**: "Session not initialized"

**Solution**: Always send an ``initialize`` request first:

.. code-block:: bash

   # Initialize session before other operations
   curl -X POST server/mcp \\
     -H "Content-Type: application/json" \\
     -H "MCP-Protocol-Version: 2025-06-18" \\
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize",...}'

**Problem**: "Unsupported protocol version"

**Solution**: Use the correct protocol version (2025-06-18):

.. code-block:: json

   {
     "params": {
       "protocolVersion": "2025-06-18"
     }
   }

Claude Desktop Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Claude can't find RMCP tools

**Solution**: Check MCP configuration and restart Claude Desktop:

.. code-block:: json

   {
     "mcpServers": {
       "rmcp": {
         "command": "rmcp",
         "args": ["start"]
       }
     }
   }

**Problem**: RMCP server won't start

**Solution**: Verify installation and dependencies:

.. code-block:: bash

   # Check if rmcp is installed
   which rmcp
   
   # Test basic functionality
   rmcp --version
   
   # Check if R is available
   which R

Network Connectivity
~~~~~~~~~~~~~~~~~~~~

**Problem**: Connection refused or timeout

**Solution**: Verify server status and network access:

.. code-block:: bash

   # Check if server is running
   curl -f https://rmcp-server-394229601724.us-central1.run.app/health
   
   # Test basic connectivity
   ping rmcp-server-394229601724.us-central1.run.app
   
   # Check if port is accessible
   telnet rmcp-server-394229601724.us-central1.run.app 443

**Problem**: CORS errors in browser

**Solution**: Server supports CORS, but check request headers:

.. code-block:: javascript

   // Ensure proper headers are set
   fetch(url, {
       method: 'POST',
       headers: {
           'Content-Type': 'application/json',
           'MCP-Protocol-Version': '2025-06-18'
       },
       body: JSON.stringify(request)
   });

R Integration Issues
--------------------

R Installation Problems
~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: "R not found" or "R command failed"

**Solution**: Verify R installation and version:

.. code-block:: bash

   # Check R installation
   R --version
   
   # Should show R version 4.4.0 or higher
   # If not installed:
   
   # macOS
   brew install r
   
   # Ubuntu/Debian
   sudo apt install r-base
   
   # CentOS/RHEL
   sudo yum install R

**Problem**: R package installation fails

**Solution**: Check package availability and permissions:

.. code-block:: bash

   # Test R package installation
   R -e "install.packages('jsonlite', repos='https://cran.r-project.org/')"
   
   # Check write permissions to R library
   R -e ".libPaths()"
   
   # Install to user library if needed
   R -e "install.packages('jsonlite', lib='~/R/library')"

**Problem**: R packages missing or wrong versions

**Solution**: Verify required packages are installed:

.. code-block:: bash

   # Check which packages are missing
   rmcp check-r-packages  # If available
   
   # Or manually install core packages
   R -e "install.packages(c('jsonlite', 'dplyr', 'ggplot2', 'broom'))"

Memory and Performance Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: "R process killed" or out of memory errors

**Solution**: Increase memory limits and optimize data:

.. code-block:: bash

   # Increase R memory limit (environment variable)
   export R_MAX_VSIZE=4G
   
   # For large datasets, consider data sampling
   # Or process data in chunks

**Problem**: R operations timeout

**Solution**: Increase timeout settings:

.. code-block:: bash

   # For HTTP server
   export RMCP_R_TIMEOUT=600  # 10 minutes
   
   # For package usage
   rmcp --timeout 600 start

**Problem**: Slow statistical operations

**Solution**: Optimize R code and data processing:

.. code-block:: bash

   # Use data.table for large datasets
   R -e "install.packages('data.table')"
   
   # Limit CPU cores for R
   export OMP_NUM_THREADS=2

Data Format Issues
------------------

CSV Parsing Problems
~~~~~~~~~~~~~~~~~~~~

**Problem**: "Error parsing CSV data"

**Solution**: Check CSV format and encoding:

.. code-block:: bash

   # Ensure proper CSV format
   # Good: "col1,col2\nval1,val2\nval3,val4"
   # Bad: "col1,col2\n val1, val2\n"  # extra spaces
   
   # Check for special characters
   # Use proper escaping for quotes and commas

**Problem**: "Column names missing or invalid"

**Solution**: Ensure CSV has proper headers:

.. code-block:: csv

   # Good format
   sales,marketing,date
   100,5,2024-01-01
   120,8,2024-01-02
   
   # Bad format (no headers)
   100,5,2024-01-01
   120,8,2024-01-02

JSON Format Issues
~~~~~~~~~~~~~~~~~~

**Problem**: "Invalid JSON format"

**Solution**: Validate JSON structure:

.. code-block:: json

   // Good format
   {
     "sales": [100, 120, 115],
     "marketing": [5, 8, 6]
   }
   
   // Bad format (trailing comma)
   {
     "sales": [100, 120, 115,],
     "marketing": [5, 8, 6]
   }

**Problem**: "Data type mismatch"

**Solution**: Ensure consistent data types:

.. code-block:: json

   // Good: all numbers
   {"values": [1, 2, 3, 4, 5]}
   
   // Bad: mixed types
   {"values": [1, "2", 3, "four", 5]}

Authentication and Security
---------------------------

Session Management
~~~~~~~~~~~~~~~~~~

**Problem**: "Session expired" or "Invalid session"

**Solution**: Implement proper session handling:

.. code-block:: python

   class RMCPClient:
       def __init__(self):
           self.session_id = None
           
       def ensure_session(self):
           if not self.session_id:
               self.initialize()
               
       def make_request(self, request):
           self.ensure_session()
           # Add session ID to headers
           headers['MCP-Session-Id'] = self.session_id

**Problem**: "Unauthorized access"

**Solution**: Check session initialization and headers:

.. code-block:: bash

   # Ensure session is properly initialized
   # Check that session ID is being passed correctly
   # Verify MCP-Protocol-Version header is included

Security Issues
~~~~~~~~~~~~~~~

**Problem**: "Package installation blocked"

**Solution**: This is expected security behavior. Approve package installation:

.. code-block:: text

   # When prompted, review the package and approve if safe
   # Or configure auto-approval for trusted packages

**Problem**: "File operation denied"

**Solution**: Check virtual file system permissions:

.. code-block:: bash

   # For HTTP server, file operations may be restricted
   # Use data input methods instead of file operations
   # Or configure VFS permissions if needed

Statistical Analysis Issues
---------------------------

Formula Syntax Errors
~~~~~~~~~~~~~~~~~~~~~~

**Problem**: "Invalid formula syntax"

**Solution**: Use proper R formula syntax:

.. code-block:: r

   # Good formulas
   "y ~ x"                    # Simple regression
   "y ~ x1 + x2"             # Multiple regression  
   "y ~ x1 * x2"             # With interaction
   "log(y) ~ poly(x, 2)"     # Transformations
   
   # Bad formulas
   "y = x"                   # Use ~ not =
   "y ~ x + "                # Incomplete formula

**Problem**: "Variable not found in data"

**Solution**: Check variable names match data:

.. code-block:: bash

   # Ensure variable names in formula exist in data
   # Check for typos and case sensitivity
   # Verify data structure before analysis

Model Convergence Issues
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: "Model failed to converge"

**Solution**: Check data quality and model specification:

.. code-block:: r

   # Check for multicollinearity
   # Scale numeric variables
   # Remove perfect predictors
   # Use simpler model specification

**Problem**: "Insufficient data for analysis"

**Solution**: Provide adequate sample size:

.. code-block:: text

   # Ensure minimum sample sizes:
   # Linear regression: 10+ observations per variable
   # Logistic regression: 20+ observations per variable
   # Time series: 30+ observations

Visualization Issues
--------------------

Plot Generation Problems
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: "Plot generation failed"

**Solution**: Check graphics dependencies and data:

.. code-block:: bash

   # Verify ggplot2 is installed
   R -e "library(ggplot2)"
   
   # Check data has enough points for visualization
   # Ensure numeric data for plots

**Problem**: "Image encoding failed"

**Solution**: Check graphics device and memory:

.. code-block:: bash

   # For HTTP server, plots are base64-encoded
   # Ensure sufficient memory for image generation
   # Try smaller plot dimensions if needed

Performance Optimization
------------------------

Server Performance
~~~~~~~~~~~~~~~~~~

**Problem**: Slow response times

**Solution**: Optimize server configuration:

.. code-block:: bash

   # Increase memory allocation
   export RMCP_MAX_MEMORY=4G
   
   # Limit concurrent operations
   export RMCP_MAX_CONCURRENT=5
   
   # Use connection pooling for HTTP clients

Client Performance
~~~~~~~~~~~~~~~~~~

**Problem**: High latency for small operations

**Solution**: Consider batch operations or local processing:

.. code-block:: python

   # Batch multiple operations
   results = []
   for data_chunk in chunks:
       result = client.analyze(data_chunk)
       results.append(result)
   
   # Or use Python package for low-latency needs
   import rmcp
   result = rmcp.descriptive_stats(data)

Debugging Tips
--------------

Enable Debug Logging
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # For Python package
   export RMCP_LOG_LEVEL=DEBUG
   rmcp start
   
   # For HTTP server
   export RMCP_LOG_LEVEL=DEBUG
   rmcp serve-http

Check Server Logs
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Docker logs
   docker logs rmcp-server
   
   # Systemd logs
   sudo journalctl -u rmcp -f
   
   # Application logs
   tail -f /var/log/rmcp/rmcp.log

Test Basic Functionality
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test health endpoint
   curl -f http://localhost:8000/health
   
   # Test MCP initialization
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | rmcp start
   
   # Test simple operation
   python -c "import rmcp; print(rmcp.descriptive_stats([1,2,3,4,5]))"

Getting Help
------------

Documentation Resources
~~~~~~~~~~~~~~~~~~~~~~~

- **Package Documentation**: :doc:`../package/user_guide/quick_start`
- **HTTP Server Guide**: :doc:`../http-server/getting-started`
- **API Reference**: :doc:`../package/api/modules`
- **GitHub Repository**: https://github.com/finite-sample/rmcp

Community Support
~~~~~~~~~~~~~~~~~

- **Issues**: https://github.com/finite-sample/rmcp/issues
- **Discussions**: https://github.com/finite-sample/rmcp/discussions
- **Examples**: :doc:`examples`

When Reporting Issues
~~~~~~~~~~~~~~~~~~~~~

Include the following information:

1. **Environment**: OS, Python version, R version
2. **Installation method**: pip, Docker, source
3. **Error messages**: Complete error logs
4. **Reproduction steps**: Minimal example
5. **Configuration**: Relevant environment variables

.. code-block:: bash

   # Collect system information
   rmcp --version
   python --version
   R --version
   
   # Include relevant logs
   # Provide minimal reproduction case