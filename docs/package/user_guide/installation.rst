Installation Guide
==================

Python Installation
-------------------

RMCP requires Python 3.9+ and can be installed via pip:

.. code-block:: bash

    pip install rmcp

Development Installation
------------------------

For development, clone the repository and install with Poetry:

.. code-block:: bash

    git clone https://github.com/finite-sample/rmcp.git
    cd rmcp
    poetry install

R Dependencies
--------------

RMCP requires several R packages for statistical analysis. Check which packages are installed:

.. code-block:: bash

    rmcp check-r-packages

Install missing R packages using R:

.. code-block:: r

    # Core packages
    install.packages(c('jsonlite', 'plm', 'lmtest', 'sandwich', 'AER', 'dplyr'))
    
    # Advanced packages  
    install.packages(c('forecast', 'vars', 'urca', 'ggplot2', 'gridExtra', 'tidyr', 'rlang'))

Docker Installation
-------------------

Use the pre-built Docker image for a complete environment:

.. code-block:: bash

    docker pull ghcr.io/finite-sample/rmcp/rmcp-ci:latest
    docker run -it ghcr.io/finite-sample/rmcp/rmcp-ci:latest

Verification
------------

Verify the installation:

.. code-block:: bash

    # Check version
    rmcp --version
    
    # List available tools (should show 40 tools)
    rmcp list-capabilities
    
    # Start the server
    rmcp start