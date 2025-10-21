Configuration Loader
====================

The configuration loader implements hierarchical configuration loading from multiple sources.

.. currentmodule:: rmcp.config.loader

Configuration Loader Class
--------------------------

.. autoclass:: ConfigLoader
   :members:
   :special-members: __init__

The ConfigLoader automatically discovers and merges configuration from:

1. Command-line arguments (highest priority)
2. Environment variables (``RMCP_*`` prefix)  
3. User configuration file (``~/.rmcp/config.json``)
4. System configuration file (``/etc/rmcp/config.json``)
5. Built-in defaults (lowest priority)

Loading Configuration
--------------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from rmcp.config.loader import ConfigLoader
   
   # Load with default discovery
   loader = ConfigLoader()
   config = loader.load_config()
   
   # Access configuration values
   print(f"HTTP server will bind to {config.http.host}:{config.http.port}")
   print(f"R timeout: {config.r.timeout} seconds")

Custom Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Load from custom file
   config = loader.load_config(config_file="/path/to/custom.json")

CLI Overrides
~~~~~~~~~~~~

.. code-block:: python

   # Load with CLI overrides
   config = loader.load_config(
       cli_overrides={
           "debug": True,
           "http": {"host": "0.0.0.0", "port": 9000},
           "r": {"timeout": 300}
       }
   )

Environment Variable Discovery
-----------------------------

.. autofunction:: discover_env_overrides

Environment variables are automatically discovered and mapped to configuration keys:

* ``RMCP_HTTP_HOST`` → ``http.host``
* ``RMCP_HTTP_PORT`` → ``http.port`` 
* ``RMCP_R_TIMEOUT`` → ``r.timeout``
* ``RMCP_LOG_LEVEL`` → ``logging.level``
* ``RMCP_DEBUG`` → ``debug``

File Loading and Validation
---------------------------

.. autofunction:: load_config_file

.. autofunction:: validate_config

Configuration files are validated against a JSON schema to ensure:

* Required fields are present
* Data types are correct
* Values are within valid ranges
* Nested structure matches expected format

Error Handling
--------------

.. autoexception:: ConfigError

Configuration errors provide detailed information about:

* Which configuration source caused the error
* Specific validation failures
* Suggestions for fixing the issue
* Schema validation details

Utility Functions
----------------

.. autofunction:: deep_merge

.. autofunction:: convert_value

.. autofunction:: get_config_file_paths

These utility functions support the configuration loading process with
type conversion, nested dictionary merging, and configuration file discovery.