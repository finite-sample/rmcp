Configuration Examples
======================

This section provides comprehensive examples for different RMCP deployment scenarios.

Development Configuration
-------------------------

Typical development setup with debugging enabled:

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Development environment variables
   export RMCP_HTTP_HOST=localhost
   export RMCP_HTTP_PORT=8000
   export RMCP_R_TIMEOUT=300
   export RMCP_LOG_LEVEL=DEBUG
   export RMCP_DEBUG=true
   
   # Start development server
   rmcp start

Configuration File
~~~~~~~~~~~~~~~~~~

Create ``~/.rmcp/config.json`` for development:

.. code-block:: json

   {
     "http": {
       "host": "localhost",
       "port": 8000
     },
     "r": {
       "timeout": 300,
       "max_sessions": 5
     },
     "security": {
       "vfs_read_only": false,
       "vfs_allowed_paths": ["/tmp", "/home/user/data"]
     },
     "logging": {
       "level": "DEBUG",
       "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
     },
     "debug": true
   }

Production Configuration
-----------------------

Secure production deployment with performance optimization:

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Production environment variables
   export RMCP_HTTP_HOST=0.0.0.0
   export RMCP_HTTP_PORT=8000
   export RMCP_R_TIMEOUT=120
   export RMCP_R_MAX_SESSIONS=50
   export RMCP_VFS_READ_ONLY=true
   export RMCP_LOG_LEVEL=INFO
   export RMCP_THREADPOOL_MAX_WORKERS=8

Configuration File  
~~~~~~~~~~~~~~~~~~

Create ``/etc/rmcp/config.json`` for production:

.. code-block:: json

   {
     "http": {
       "host": "0.0.0.0",
       "port": 8000,
       "cors_origins": [
         "https://myapp.example.com",
         "https://analytics.example.com"
       ]
     },
     "r": {
       "timeout": 120,
       "session_timeout": 1800,
       "max_sessions": 50
     },
     "security": {
       "vfs_max_file_size": 104857600,
       "vfs_read_only": true,
       "vfs_allowed_paths": ["/data/readonly"]
     },
     "performance": {
       "threadpool_max_workers": 8,
       "callback_timeout": 600
     },
     "logging": {
       "level": "INFO",
       "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
     }
   }

SSL/HTTPS Configuration
-----------------------

Secure HTTPS deployment with SSL certificates:

.. code-block:: json

   {
     "http": {
       "host": "0.0.0.0",
       "port": 443,
       "ssl_keyfile": "/etc/ssl/private/rmcp.key",
       "ssl_certfile": "/etc/ssl/certs/rmcp.crt",
       "cors_origins": ["https://secure.example.com"]
     },
     "security": {
       "vfs_read_only": true,
       "vfs_max_file_size": 52428800
     },
     "logging": {
       "level": "WARNING"
     }
   }

Docker Configuration
-------------------

Configuration for containerized deployment:

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Docker environment variables
   docker run -d \\
     -e RMCP_HTTP_HOST=0.0.0.0 \\
     -e RMCP_HTTP_PORT=8000 \\
     -e RMCP_R_TIMEOUT=180 \\
     -e RMCP_R_MAX_SESSIONS=20 \\
     -e RMCP_LOG_LEVEL=INFO \\
     -p 8000:8000 \\
     rmcp:latest \\
     rmcp serve-http

Volume-Mounted Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Create configuration file
   cat > /host/path/config.json << EOF
   {
     "http": {"host": "0.0.0.0", "port": 8000},
     "r": {"timeout": 180, "max_sessions": 20},
     "security": {"vfs_read_only": true},
     "logging": {"level": "INFO"}
   }
   EOF
   
   # Run with mounted configuration
   docker run -d \\
     -v /host/path/config.json:/etc/rmcp/config.json \\
     -p 8000:8000 \\
     rmcp:latest \\
     rmcp serve-http

High-Performance Configuration
-----------------------------

Optimized for high-throughput scenarios:

.. code-block:: json

   {
     "http": {
       "host": "0.0.0.0",
       "port": 8000
     },
     "r": {
       "timeout": 60,
       "session_timeout": 900,
       "max_sessions": 100
     },
     "security": {
       "vfs_max_file_size": 209715200,
       "vfs_read_only": true
     },
     "performance": {
       "threadpool_max_workers": 16,
       "callback_timeout": 300,
       "process_cleanup_timeout": 2
     },
     "logging": {
       "level": "WARNING"
     }
   }

Resource-Constrained Configuration
---------------------------------

Minimal resource usage for limited environments:

.. code-block:: json

   {
     "http": {
       "host": "localhost",
       "port": 8000
     },
     "r": {
       "timeout": 120,
       "session_timeout": 1800,
       "max_sessions": 3
     },
     "security": {
       "vfs_max_file_size": 10485760,
       "vfs_read_only": true
     },
     "performance": {
       "threadpool_max_workers": 1,
       "callback_timeout": 120
     },
     "logging": {
       "level": "ERROR"
     }
   }

Command-Line Examples
--------------------

Override configuration via command line:

.. code-block:: bash

   # Custom config file
   rmcp --config /path/to/custom.json start
   
   # Enable debug mode
   rmcp --debug start
   
   # HTTP server with custom settings
   rmcp serve-http --host 0.0.0.0 --port 9000
   
   # Override log level
   rmcp start --log-level DEBUG
   
   # Multiple overrides
   rmcp --config prod.json --debug serve-http --port 9000