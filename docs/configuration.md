# Configuration System

RMCP includes a comprehensive configuration management system that supports multiple configuration sources with a clear priority order.

## Configuration Sources (Priority Order)

1. **Command-line arguments** (highest priority)
2. **Environment variables** (`RMCP_*` prefix)
3. **User config file** (`~/.rmcp/config.json`)
4. **System config file** (`/etc/rmcp/config.json`)
5. **Built-in defaults** (lowest priority)

## Development Configuration

### Environment Variables
```bash
# Environment variables for development
export RMCP_LOG_LEVEL=DEBUG
export RMCP_HTTP_PORT=9000
export RMCP_R_TIMEOUT=300
```

### Configuration File
```bash
# Configuration file for development
echo '{"debug": true, "logging": {"level": "DEBUG"}}' > ~/.rmcp/config.json
```

### CLI Options
```bash
# CLI options override everything
uv run rmcp --debug --config custom.json start
```

## Docker Configuration

### Environment Variables in Docker
```bash
docker run -e RMCP_HTTP_HOST=0.0.0.0 -e RMCP_HTTP_PORT=8000 rmcp:latest
```

### Mount Configuration File
```bash
docker run -v $(pwd)/config.json:/etc/rmcp/config.json rmcp:latest
```

## Configuration Examples

### Production Configuration
```json
{
  "debug": false,
  "logging": {
    "level": "INFO",
    "format": "json"
  },
  "http": {
    "host": "0.0.0.0",
    "port": 8000,
    "cors_origins": ["https://yourdomain.com"]
  },
  "r": {
    "timeout": 300,
    "memory_limit": "2GB"
  }
}
```

### High-Performance Configuration
```json
{
  "r": {
    "timeout": 600,
    "memory_limit": "8GB",
    "parallel_workers": 4
  },
  "http": {
    "workers": 8,
    "max_connections": 1000
  }
}
```

## Configuration API Documentation

For complete configuration options and validation, see the auto-generated API documentation:

```{eval-rst}
.. automodule:: rmcp.config.models
   :members:
   :show-inheritance:
   :no-index:
```
