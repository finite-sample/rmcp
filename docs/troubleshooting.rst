Troubleshooting
===============

Common Issues
-------------

R Packages Not Found
~~~~~~~~~~~~~~~~~~~~~

If you get errors about missing R packages, install all required packages:

.. code-block:: r

    install.packages(c(
      "jsonlite", "plm", "lmtest", "sandwich", "AER", "dplyr",
      "forecast", "vars", "urca", "tseries", "nortest", "car",
      "rpart", "randomForest", "ggplot2", "gridExtra", "tidyr", 
      "rlang", "knitr", "broom"
    ))

Server Won't Start
~~~~~~~~~~~~~~~~~~

1. **Check R Installation**:

   .. code-block:: bash

       R --version

2. **Check Python Version**:

   .. code-block:: bash

       python --version  # Should be 3.10+

3. **Reinstall RMCP**:

   .. code-block:: bash

       pip uninstall rmcp
       pip install rmcp

MCP Client Connection Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Verify server is running**:

   .. code-block:: bash

       rmcp start --log-level DEBUG

2. **Check configuration** in your MCP client (e.g., Claude Desktop config)

3. **Restart both server and client**

Getting Help
------------

* Check the `GitHub Issues <https://github.com/finite-sample/rmcp/issues>`_
* Review the :doc:`user_guide/quick_start` guide
* Examine the :doc:`api/modules` for detailed function documentation