Configuration Models
===================

The configuration data models define the complete structure of RMCP configuration
with type hints, defaults, and validation.

.. currentmodule:: rmcp.config.models

Main Configuration
------------------

.. autoclass:: RMCPConfig
   :members:
   :special-members: __init__

HTTP Configuration
------------------

.. autoclass:: HTTPConfig
   :members:

The HTTPConfig class controls HTTP server behavior including:

* Server binding address and port
* SSL/TLS configuration  
* CORS origins for cross-origin requests
* Security considerations for production deployment

R Configuration
---------------

.. autoclass:: RConfig
   :members:

The RConfig class manages R process execution:

* Script execution timeouts
* Session lifecycle management
* Resource limits and concurrency
* Custom R binary path configuration

Security Configuration
----------------------

.. autoclass:: SecurityConfig
   :members:

The SecurityConfig class controls Virtual File System (VFS) security:

* File size limits and access restrictions
* Read-only mode for production safety
* Allowed filesystem paths
* MIME type restrictions

Performance Configuration
-------------------------

.. autoclass:: PerformanceConfig
   :members:

The PerformanceConfig class manages resource usage:

* Thread pool sizing for concurrency
* Timeout configuration for operations
* Process cleanup and resource management

Logging Configuration
--------------------

.. autoclass:: LoggingConfig
   :members:

The LoggingConfig class controls log output:

* Log level configuration (DEBUG, INFO, WARNING, ERROR, CRITICAL)
* Log message formatting
* Output destination configuration

Configuration Errors
--------------------

.. autoexception:: rmcp.config.loader.ConfigError
   :members:

This exception is raised when configuration loading, validation, or parsing fails.
It provides detailed error messages to help users fix configuration issues.