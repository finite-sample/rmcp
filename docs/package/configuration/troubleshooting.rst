Configuration Troubleshooting
=============================

This section helps diagnose and fix common configuration issues.

Configuration Not Loading
-------------------------

Check File Permissions
~~~~~~~~~~~~~~~~~~~~~~

Configuration files must be readable by the RMCP process:

.. code-block:: bash

   # Check file permissions
   ls -la ~/.rmcp/config.json
   ls -la /etc/rmcp/config.json
   
   # Fix permissions if needed
   chmod 644 ~/.rmcp/config.json
   sudo chmod 644 /etc/rmcp/config.json

Verify JSON Syntax
~~~~~~~~~~~~~~~~~~

Configuration files must be valid JSON:

.. code-block:: bash

   # Validate JSON syntax
   python -m json.tool ~/.rmcp/config.json
   
   # Or use jq if available
   jq . ~/.rmcp/config.json

Check Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~

List all RMCP environment variables:

.. code-block:: bash

   # List RMCP environment variables
   env | grep RMCP_
   
   # Check specific variable
   echo $RMCP_HTTP_PORT

Enable Debug Mode
~~~~~~~~~~~~~~~~

Use debug mode to see configuration loading details:

.. code-block:: bash

   # Command line debug
   rmcp --debug start
   
   # Environment variable
   export RMCP_DEBUG=true
   rmcp start
   
   # Config file debug
   echo '{"debug": true}' > ~/.rmcp/config.json
   rmcp start

Invalid Configuration Values
----------------------------

Port Number Issues
~~~~~~~~~~~~~~~~~

Ports must be between 1-65535:

.. code-block:: bash

   # Invalid port (will fail)
   export RMCP_HTTP_PORT=70000
   
   # Valid port
   export RMCP_HTTP_PORT=8080

Timeout Configuration
~~~~~~~~~~~~~~~~~~~~

Timeouts must be positive integers:

.. code-block:: json

   {
     "r": {
       "timeout": 180,         // Valid: positive integer
       "session_timeout": 3600 // Valid: positive integer
     }
   }

File Size Limits
~~~~~~~~~~~~~~~

File sizes must be positive integers (bytes):

.. code-block:: json

   {
     "security": {
       "vfs_max_file_size": 52428800  // Valid: 50MB in bytes
     }
   }

Log Level Validation
~~~~~~~~~~~~~~~~~~~

Log levels must be valid Python logging levels:

.. code-block:: bash

   # Valid log levels
   export RMCP_LOG_LEVEL=DEBUG
   export RMCP_LOG_LEVEL=INFO
   export RMCP_LOG_LEVEL=WARNING
   export RMCP_LOG_LEVEL=ERROR
   export RMCP_LOG_LEVEL=CRITICAL
   
   # Invalid log level (will fail)
   export RMCP_LOG_LEVEL=VERBOSE

Environment Variable Issues
--------------------------

Variable Naming
~~~~~~~~~~~~~~

Environment variables must use the ``RMCP_`` prefix and exact names:

.. code-block:: bash

   # Correct
   export RMCP_HTTP_HOST=0.0.0.0
   export RMCP_HTTP_PORT=8000
   
   # Incorrect (will be ignored)
   export HTTP_HOST=0.0.0.0
   export RMCP_HOST=0.0.0.0

List Values
~~~~~~~~~~

Use commas to separate list items:

.. code-block:: bash

   # Correct: comma-separated values
   export RMCP_HTTP_CORS_ORIGINS="https://app1.com,https://app2.com"
   export RMCP_VFS_ALLOWED_PATHS="/data,/tmp,/home/user"
   
   # Incorrect: spaces will not work
   export RMCP_HTTP_CORS_ORIGINS="https://app1.com https://app2.com"

Boolean Values
~~~~~~~~~~~~~

Use standard boolean representations:

.. code-block:: bash

   # Valid boolean values
   export RMCP_DEBUG=true
   export RMCP_DEBUG=false
   export RMCP_DEBUG=1
   export RMCP_DEBUG=0
   export RMCP_DEBUG=yes
   export RMCP_DEBUG=no
   export RMCP_DEBUG=on
   export RMCP_DEBUG=off

SSL Configuration Issues
------------------------

Missing SSL Files
~~~~~~~~~~~~~~~~

Both SSL key and certificate files must be provided:

.. code-block:: json

   {
     "http": {
       "ssl_keyfile": "/etc/ssl/private/rmcp.key",    // Both required
       "ssl_certfile": "/etc/ssl/certs/rmcp.crt"      // Both required
     }
   }

File Path Validation
~~~~~~~~~~~~~~~~~~~

SSL files must exist and be readable:

.. code-block:: bash

   # Check SSL files exist
   ls -la /etc/ssl/private/rmcp.key
   ls -la /etc/ssl/certs/rmcp.crt
   
   # Check permissions
   sudo chmod 600 /etc/ssl/private/rmcp.key
   sudo chmod 644 /etc/ssl/certs/rmcp.crt

R Configuration Issues
---------------------

R Binary Not Found
~~~~~~~~~~~~~~~~~~

If R is not in PATH, specify the full path:

.. code-block:: json

   {
     "r": {
       "binary_path": "/usr/local/bin/R"
     }
   }

Session Limits
~~~~~~~~~~~~~

Ensure session limits match available memory:

.. code-block:: json

   {
     "r": {
       "max_sessions": 10,     // ~1-2GB memory required
       "session_timeout": 3600 // Clean up idle sessions
     }
   }

Security Configuration Issues
----------------------------

VFS Path Access
~~~~~~~~~~~~~~

Ensure allowed paths exist and are accessible:

.. code-block:: bash

   # Check path exists
   ls -la /data/allowed/path
   
   # Check permissions
   chmod 755 /data/allowed/path

Read-Only Mode
~~~~~~~~~~~~~

In production, keep VFS in read-only mode:

.. code-block:: json

   {
     "security": {
       "vfs_read_only": true,  // Recommended for production
       "vfs_allowed_paths": ["/data/readonly"]
     }
   }

Configuration Debugging Commands
-------------------------------

Complete Diagnostic
~~~~~~~~~~~~~~~~~~~

Run these commands to diagnose configuration issues:

.. code-block:: bash

   # 1. Check configuration file syntax
   python -m json.tool ~/.rmcp/config.json
   
   # 2. List environment variables
   env | grep RMCP_ | sort
   
   # 3. Test configuration loading
   rmcp --debug start --dry-run
   
   # 4. Check file permissions
   ls -la ~/.rmcp/config.json /etc/rmcp/config.json
   
   # 5. Validate paths exist
   ls -la /path/to/ssl/files

Configuration Validation
~~~~~~~~~~~~~~~~~~~~~~~~

Enable verbose validation output:

.. code-block:: bash

   # Show configuration loading details
   RMCP_DEBUG=true rmcp start
   
   # Show final resolved configuration
   rmcp config show
   
   # Validate configuration without starting
   rmcp config validate

Common Error Messages
--------------------

"HTTP port must be between 1-65535"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fix: Set a valid port number:

.. code-block:: bash

   export RMCP_HTTP_PORT=8000

"SSL key file is required when SSL certificate is specified"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fix: Provide both SSL files:

.. code-block:: bash

   export RMCP_HTTP_SSL_KEYFILE=/path/to/key.pem
   export RMCP_HTTP_SSL_CERTFILE=/path/to/cert.pem

"Configuration file not found"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fix: Create configuration file or specify correct path:

.. code-block:: bash

   # Create default config directory
   mkdir -p ~/.rmcp
   
   # Use custom config file
   rmcp --config /path/to/config.json start

"Log level must be one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fix: Use a valid log level:

.. code-block:: bash

   export RMCP_LOG_LEVEL=INFO