Configuration System
===================

RMCP provides a comprehensive, hierarchical configuration system that supports multiple configuration sources
with automatic validation and type conversion.

.. toctree::
   :maxdepth: 2
   :caption: Configuration

   overview
   models
   loader
   examples
   troubleshooting

Configuration Overview
---------------------

Configuration values are resolved in priority order:

1. **Command-line arguments** (highest priority)
2. **Environment variables** (``RMCP_*`` prefix)
3. **User configuration file** (``~/.rmcp/config.json``)
4. **System configuration file** (``/etc/rmcp/config.json``)
5. **Built-in defaults** (lowest priority)

Quick Start
-----------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Set configuration via environment variables with ``RMCP_*`` prefix:

.. code-block:: bash

   export RMCP_HTTP_HOST=0.0.0.0
   export RMCP_HTTP_PORT=9000
   export RMCP_R_TIMEOUT=180
   export RMCP_LOG_LEVEL=DEBUG

Configuration File
~~~~~~~~~~~~~~~~~~

Create ``~/.rmcp/config.json``:

.. code-block:: json

   {
     "http": {
       "host": "0.0.0.0",
       "port": 9000,
       "cors_origins": ["https://myapp.example.com"]
     },
     "r": {
       "timeout": 180,
       "max_sessions": 20
     },
     "security": {
       "vfs_read_only": false,
       "vfs_allowed_paths": ["/data", "/tmp"]
     },
     "logging": {
       "level": "DEBUG"
     },
     "debug": true
   }

Command Line
~~~~~~~~~~~~

Override any setting via command line:

.. code-block:: bash

   rmcp --config /path/to/config.json --debug start
   rmcp serve-http --host 0.0.0.0 --port 9000

API Reference
-------------

The configuration system is implemented across three main modules:

.. autosummary::
   :toctree: _autosummary
   :template: module.rst

   rmcp.config.models
   rmcp.config.loader
   rmcp.config.defaults