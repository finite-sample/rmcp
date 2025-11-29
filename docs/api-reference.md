# API Reference

Complete API documentation for RMCP components.

## Core Modules

### Server
```{eval-rst}
.. automodule:: rmcp.core.server
   :members:
   :show-inheritance:
```

### Context Management
```{eval-rst}
.. automodule:: rmcp.core.context
   :members:
   :show-inheritance:
```

## Statistical Tools

### Regression Analysis
```{eval-rst}
.. automodule:: rmcp.tools.regression
   :members:
   :show-inheritance:
```

### Visualization Tools
```{eval-rst}
.. automodule:: rmcp.tools.visualization
   :members:
   :show-inheritance:
```

### Time Series Analysis
```{eval-rst}
.. automodule:: rmcp.tools.timeseries
   :members:
   :show-inheritance:
```

### Machine Learning
```{eval-rst}
.. automodule:: rmcp.tools.machine_learning
   :members:
   :show-inheritance:
```

### Statistical Tests
```{eval-rst}
.. automodule:: rmcp.tools.statistical_tests
   :members:
   :show-inheritance:
```

### Econometrics
```{eval-rst}
.. automodule:: rmcp.tools.econometrics
   :members:
   :show-inheritance:
```

## R Integration

### R Integration Core
```{eval-rst}
.. automodule:: rmcp.r_integration
   :members:
   :show-inheritance:
```

## Configuration System

### Configuration Models
```{eval-rst}
.. automodule:: rmcp.config.models
   :members:
   :show-inheritance:
```

### Configuration Loader
```{eval-rst}
.. automodule:: rmcp.config.loader
   :members:
   :show-inheritance:
```

## Transport Layer

### Base Transport
```{eval-rst}
.. automodule:: rmcp.transport.base
   :members:
   :show-inheritance:
```

### HTTP Transport
The HTTP transport module requires optional HTTP dependencies (`fastapi`, `uvicorn`).
Install with: `pip install rmcp[http]`

For HTTP API documentation, see [HTTP Server API](http-api.md).

## Registries

### Tool Registry
```{eval-rst}
.. automodule:: rmcp.registries.tools
   :members:
   :show-inheritance:
```

### Resource Registry
```{eval-rst}
.. automodule:: rmcp.registries.resources
   :members:
   :show-inheritance:
```
