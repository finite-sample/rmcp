# RMCP Configuration Guide

RMCP provides a flexible, hierarchical configuration system that allows you to customize server behavior through environment variables, configuration files, and command-line options.

## Configuration Hierarchy

Configuration values are resolved in the following order (highest to lowest priority):

1. **Command-line arguments** (highest priority)
2. **Environment variables** (`RMCP_*` prefix)
3. **User configuration file** (`~/.rmcp/config.json`)
4. **System configuration file** (`/etc/rmcp/config.json`)
5. **Built-in defaults** (lowest priority)

## Configuration Options

### HTTP Transport

| Setting | Default | Environment Variable | Description |
|---------|---------|---------------------|-------------|
| `http.host` | `"localhost"` | `RMCP_HTTP_HOST` | HTTP server binding address |
| `http.port` | `8000` | `RMCP_HTTP_PORT` | HTTP server port |
| `http.cors_origins` | `["http://localhost:*", ...]` | `RMCP_HTTP_CORS_ORIGINS` | Allowed CORS origins (comma-separated) |

### R Process Configuration

| Setting | Default | Environment Variable | Description |
|---------|---------|---------------------|-------------|
| `r.timeout` | `120` | `RMCP_R_TIMEOUT` | R script execution timeout (seconds) |
| `r.session_timeout` | `3600` | `RMCP_R_SESSION_TIMEOUT` | R session lifetime (seconds) |
| `r.max_sessions` | `10` | `RMCP_R_MAX_SESSIONS` | Maximum concurrent R sessions |
| `r.binary_path` | `null` | `RMCP_R_BINARY_PATH` | Custom R binary path (auto-detect if null) |
| `r.version_check_timeout` | `30` | `RMCP_R_VERSION_CHECK_TIMEOUT` | R version check timeout (seconds) |

### Security Configuration

| Setting | Default | Environment Variable | Description |
|---------|---------|---------------------|-------------|
| `security.vfs_max_file_size` | `52428800` | `RMCP_VFS_MAX_FILE_SIZE` | Maximum file size for VFS (bytes) |
| `security.vfs_allowed_paths` | `[]` | `RMCP_VFS_ALLOWED_PATHS` | Additional allowed filesystem paths (comma-separated) |
| `security.vfs_read_only` | `true` | `RMCP_VFS_READ_ONLY` | Enable VFS read-only mode |

### Performance Configuration

| Setting | Default | Environment Variable | Description |
|---------|---------|---------------------|-------------|
| `performance.threadpool_max_workers` | `2` | `RMCP_THREADPOOL_MAX_WORKERS` | Max workers for stdio transport |
| `performance.callback_timeout` | `300` | `RMCP_CALLBACK_TIMEOUT` | Bidirectional callback timeout (seconds) |
| `performance.process_cleanup_timeout` | `5` | `RMCP_PROCESS_CLEANUP_TIMEOUT` | Process cleanup timeout (seconds) |

### Logging Configuration

| Setting | Default | Environment Variable | Description |
|---------|---------|---------------------|-------------|
| `logging.level` | `"INFO"` | `RMCP_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `logging.format` | `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"` | `RMCP_LOG_FORMAT` | Log message format string |

### Global Settings

| Setting | Default | Environment Variable | Description |
|---------|---------|---------------------|-------------|
| `debug` | `false` | `RMCP_DEBUG` | Enable debug mode |

## Configuration Methods

### 1. Environment Variables

All environment variables use the `RMCP_` prefix:

```bash
# Set HTTP configuration
export RMCP_HTTP_HOST=0.0.0.0
export RMCP_HTTP_PORT=9000

# Set R configuration
export RMCP_R_TIMEOUT=180
export RMCP_R_MAX_SESSIONS=20

# Set logging
export RMCP_LOG_LEVEL=DEBUG

# Start server with environment config
rmcp start
```

### 2. Configuration File

Create a configuration file at `~/.rmcp/config.json`:

```json
{
  "http": {
    "host": "0.0.0.0",
    "port": 9000,
    "cors_origins": [
      "http://localhost:*",
      "http://127.0.0.1:*",
      "https://myapp.example.com"
    ]
  },
  "r": {
    "timeout": 180,
    "session_timeout": 7200,
    "max_sessions": 20,
    "binary_path": "/usr/local/bin/R"
  },
  "security": {
    "vfs_max_file_size": 104857600,
    "vfs_allowed_paths": ["/data", "/home/user/datasets"],
    "vfs_read_only": false
  },
  "performance": {
    "threadpool_max_workers": 4,
    "callback_timeout": 600
  },
  "logging": {
    "level": "DEBUG",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
  },
  "debug": true
}
```

### 3. Command-Line Options

Use CLI options to override configuration:

```bash
# Override config file location
rmcp --config /path/to/custom/config.json start

# Enable debug mode
rmcp --debug start

# Override HTTP settings
rmcp serve-http --host 0.0.0.0 --port 9000

# Override log level
rmcp start --log-level DEBUG
```

## Common Configuration Examples

### Development Configuration

```json
{
  "http": {
    "host": "localhost",
    "port": 8000
  },
  "r": {
    "timeout": 300
  },
  "logging": {
    "level": "DEBUG"
  },
  "debug": true
}
```

### Production Configuration

```json
{
  "http": {
    "host": "0.0.0.0",
    "port": 8000,
    "cors_origins": ["https://myapp.example.com"]
  },
  "r": {
    "timeout": 120,
    "session_timeout": 1800,
    "max_sessions": 50
  },
  "security": {
    "vfs_max_file_size": 104857600,
    "vfs_read_only": true
  },
  "performance": {
    "threadpool_max_workers": 8,
    "callback_timeout": 600
  },
  "logging": {
    "level": "INFO"
  }
}
```

### Docker Configuration

Use environment variables in Docker:

```bash
docker run -d \
  -e RMCP_HTTP_HOST=0.0.0.0 \
  -e RMCP_HTTP_PORT=8000 \
  -e RMCP_R_TIMEOUT=180 \
  -e RMCP_LOG_LEVEL=INFO \
  -p 8000:8000 \
  rmcp:latest \
  rmcp serve-http
```

Or mount a configuration file:

```bash
docker run -d \
  -v /path/to/config.json:/etc/rmcp/config.json \
  -p 8000:8000 \
  rmcp:latest \
  rmcp serve-http
```

## Configuration Validation

RMCP validates configuration values on startup:

- **Network values**: Ports must be between 1-65535
- **Timeouts**: Must be positive integers
- **File sizes**: Must be positive integers
- **Log levels**: Must be valid Python logging levels
- **Boolean values**: Accept `true`/`false`, `1`/`0`, `yes`/`no`, `on`/`off`

Invalid configuration will cause startup to fail with a descriptive error message.

## Configuration Debugging

Enable debug mode to see configuration loading details:

```bash
# Command line debug
rmcp --debug start

# Environment variable
export RMCP_DEBUG=true
rmcp start

# Config file
echo '{"debug": true}' > ~/.rmcp/config.json
rmcp start
```

This will show:
- Which configuration files were loaded
- Which environment variables were applied
- Final resolved configuration values
- Any configuration warnings or errors

## Security Considerations

### HTTP Binding

- **Default**: RMCP binds to `localhost` for security
- **Remote access**: Set `RMCP_HTTP_HOST=0.0.0.0` but implement authentication
- **CORS**: Configure `cors_origins` appropriately for web clients

### File System Access

- **Read-only mode**: Keep `vfs_read_only=true` in production
- **Allowed paths**: Restrict `vfs_allowed_paths` to necessary directories
- **File size limits**: Set appropriate `vfs_max_file_size` limits

### Process Limits

- **R sessions**: Limit `r.max_sessions` based on available memory
- **Timeouts**: Set reasonable `r.timeout` to prevent runaway processes
- **Workers**: Adjust `threadpool_max_workers` based on CPU cores

## Troubleshooting

### Configuration Not Loading

1. **Check file permissions**: Configuration files must be readable
2. **Verify JSON syntax**: Use `python -m json.tool config.json` to validate
3. **Check environment variables**: Use `env | grep RMCP_` to list variables
4. **Enable debug mode**: Add `--debug` to see configuration loading process

### Invalid Configuration Values

1. **Check validation errors**: RMCP will show specific validation failures
2. **Verify data types**: Numbers should be numbers, booleans should be booleans
3. **Check ranges**: Ports, timeouts, and sizes must be within valid ranges

### Environment Variable Issues

1. **Check variable names**: Must use `RMCP_` prefix and exact names
2. **List values**: Use commas to separate list items
3. **Boolean values**: Use `true`/`false`, `1`/`0`, `yes`/`no`, or `on`/`off`