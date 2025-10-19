Configuration Overview
=====================

RMCP's configuration system provides flexible, hierarchical configuration loading
from multiple sources with automatic validation and type conversion.

Configuration Hierarchy
-----------------------

Configuration values are resolved in the following priority order:

1. **Command-line arguments** (highest priority)
2. **Environment variables** (``RMCP_*`` prefix)
3. **User configuration file** (``~/.rmcp/config.json``)
4. **System configuration file** (``/etc/rmcp/config.json``)
5. **Built-in defaults** (lowest priority)

This hierarchy allows for flexible deployment scenarios where:

* Defaults provide sensible starting values
* System-wide configuration sets organizational policies
* User configuration customizes personal preferences
* Environment variables override settings for specific deployments
* Command-line arguments provide immediate overrides for testing

Configuration Sources
--------------------

Built-in Defaults
~~~~~~~~~~~~~~~~~

RMCP includes sensible defaults for all configuration options:

* HTTP server binds to ``localhost:8000`` for security
* R timeout set to 120 seconds to prevent runaway processes
* VFS read-only mode enabled for security
* INFO-level logging for operational visibility

System Configuration
~~~~~~~~~~~~~~~~~~~

System administrators can set organization-wide defaults in ``/etc/rmcp/config.json``:

.. code-block:: json

   {
     "security": {
       "vfs_read_only": true,
       "vfs_allowed_paths": ["/data/company"]
     },
     "r": {
       "max_sessions": 50,
       "timeout": 120
     },
     "logging": {
       "level": "INFO"
     }
   }

User Configuration
~~~~~~~~~~~~~~~~~

Individual users can customize settings in ``~/.rmcp/config.json``:

.. code-block:: json

   {
     "http": {
       "port": 8080
     },
     "logging": {
       "level": "DEBUG"
     },
     "debug": true
   }

Environment Variables
~~~~~~~~~~~~~~~~~~~~

All configuration options support environment variable overrides with ``RMCP_*`` prefix:

.. code-block:: bash

   export RMCP_HTTP_HOST=0.0.0.0
   export RMCP_HTTP_PORT=9000
   export RMCP_LOG_LEVEL=DEBUG

Command-Line Arguments
~~~~~~~~~~~~~~~~~~~~~

Command-line arguments provide the highest priority overrides:

.. code-block:: bash

   rmcp --config custom.json --debug serve-http --port 9000

Configuration Categories
-----------------------

HTTP Transport
~~~~~~~~~~~~~

Controls HTTP server behavior:

* Server binding address and port
* SSL/TLS configuration
* CORS origins for web clients
* Security considerations

R Process Management
~~~~~~~~~~~~~~~~~~~

Manages R process execution:

* Script execution timeouts
* Session lifecycle and limits
* Resource management
* Custom R binary configuration

Security Controls
~~~~~~~~~~~~~~~~

Virtual File System (VFS) security:

* File access restrictions
* Read-only mode enforcement
* File size and type limits
* Allowed filesystem paths

Performance Tuning
~~~~~~~~~~~~~~~~~

Resource and performance management:

* Thread pool configuration
* Timeout settings
* Process cleanup controls
* Concurrency limits

Logging Configuration
~~~~~~~~~~~~~~~~~~~~

Log output control:

* Log levels and formatting
* Output destinations
* Debug mode settings

Configuration Validation
------------------------

Automatic Validation
~~~~~~~~~~~~~~~~~~~

RMCP automatically validates all configuration:

* **Type checking**: Ensures values match expected types
* **Range validation**: Ports, timeouts, and sizes within valid ranges
* **File validation**: SSL certificates and paths exist if specified
* **Dependency validation**: Related settings are consistent

Schema Validation
~~~~~~~~~~~~~~~~

Configuration files are validated against a JSON schema:

* Required fields must be present
* Additional properties are allowed for extensibility
* Nested structure must match expected format
* Value constraints are enforced

Error Reporting
~~~~~~~~~~~~~~

Configuration errors provide detailed information:

* Source of the error (file, environment variable, CLI)
* Specific validation failure
* Suggested fixes
* Example valid configurations

Common Patterns
--------------

Development Setup
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Quick development setup
   export RMCP_DEBUG=true
   export RMCP_LOG_LEVEL=DEBUG
   export RMCP_VFS_READ_ONLY=false
   rmcp start

Production Deployment
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Production with system config
   sudo tee /etc/rmcp/config.json << EOF
   {
     "http": {"host": "0.0.0.0", "port": 8000},
     "security": {"vfs_read_only": true},
     "r": {"max_sessions": 100},
     "logging": {"level": "INFO"}
   }
   EOF
   
   rmcp serve-http

Docker Deployment
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Environment-based Docker config
   docker run -e RMCP_HTTP_HOST=0.0.0.0 \\
              -e RMCP_R_MAX_SESSIONS=20 \\
              -p 8000:8000 rmcp:latest

Configuration Best Practices
----------------------------

Security
~~~~~~~

* Keep VFS in read-only mode for production
* Restrict allowed paths to necessary directories
* Use SSL/TLS for external access
* Set appropriate file size limits

Performance
~~~~~~~~~~

* Tune session limits based on available memory
* Adjust timeouts for your workload
* Configure thread pools for your CPU count
* Monitor resource usage and adjust accordingly

Maintenance
~~~~~~~~~~

* Use configuration files for persistent settings
* Use environment variables for deployment-specific overrides
* Document configuration choices in deployment scripts
* Validate configuration in CI/CD pipelines

Monitoring
~~~~~~~~~

* Enable appropriate logging levels
* Use debug mode for troubleshooting
* Monitor configuration loading in application logs
* Set up alerts for configuration validation failures