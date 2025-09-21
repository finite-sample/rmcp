Quick Start Guide
=================

This guide will get you up and running with RMCP in minutes.

Starting the Server
-------------------

1. **Install RMCP**:

   .. code-block:: bash

       pip install rmcp

2. **Check R packages**:

   .. code-block:: bash

       rmcp check-r-packages

3. **Start the MCP server**:

   .. code-block:: bash

       rmcp start

Basic Usage Examples
--------------------

Linear Regression
~~~~~~~~~~~~~~~~~

.. code-block:: json

    {
        "tool": "linear_model",
        "data": {
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10]
        },
        "formula": "y ~ x"
    }

Correlation Analysis
~~~~~~~~~~~~~~~~~~~

.. code-block:: json

    {
        "tool": "correlation_analysis", 
        "data": {
            "var1": [1, 2, 3, 4, 5],
            "var2": [2, 4, 6, 8, 10],
            "var3": [1, 3, 5, 7, 9]
        }
    }

Visualization with Inline Display
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

    {
        "tool": "scatter_plot",
        "data": {
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10]
        },
        "x_var": "x",
        "y_var": "y", 
        "return_image": true
    }

Working with Real Data
----------------------

Load Example Datasets
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

    {
        "tool": "load_example",
        "dataset_name": "sales",
        "size": "small"
    }

Import Your Data
~~~~~~~~~~~~~~~

.. code-block:: json

    {
        "tool": "read_csv",
        "file_path": "/path/to/your/data.csv"
    }

Natural Language Formula Building
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: json

    {
        "tool": "build_formula",
        "description": "predict sales from marketing spend"
    }

Error Recovery
~~~~~~~~~~~~~~

.. code-block:: json

    {
        "tool": "suggest_fix",
        "error_message": "object 'sales' not found",
        "tool_name": "linear_model"
    }

Next Steps
----------

* :doc:`../troubleshooting` - Troubleshooting common issues
* :doc:`../api/modules` - Complete API reference