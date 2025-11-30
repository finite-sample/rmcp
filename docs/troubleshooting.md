# Troubleshooting

Common issues and solutions for RMCP installation, configuration, and usage.

## Installation Issues

### Python Version Compatibility
**Issue**: RMCP requires Python 3.11+

**Solution**:
```bash
# Check Python version
python --version

# Install Python 3.11+ if needed
# macOS with Homebrew:
brew install python@3.11

# Ubuntu/Debian:
sudo apt update && sudo apt install python3.11

# Windows: Download from python.org
```

### Package Installation Failures
**Issue**: `pip install rmcp` fails

**Solutions**:
```bash
# Upgrade pip first
pip install --upgrade pip

# Try with user flag
pip install --user rmcp

# Use uv (recommended)
pip install uv
uv pip install rmcp
```

## R Integration Issues

### R Not Found
**Issue**: "R not found" or R script errors

**Solution**: Use Docker for guaranteed R environment:
```bash
docker build -f docker/Dockerfile --target development -t rmcp-dev .
docker run -v $(pwd):/workspace -it rmcp-dev bash
```

### R Package Missing
**Issue**: R statistical tools fail due to missing packages

**Solution**: RMCP manages R packages automatically through the security whitelist. If you see package errors:

1. Check available packages: `rmcp list-r-packages`
2. The missing package may require approval
3. Use Docker for complete package environment

## Configuration Issues

### Port Already in Use
**Issue**: "Port 8000 already in use" for HTTP server

**Solutions**:
```bash
# Use different port
rmcp serve-http --port 8080

# Or via environment variable
export RMCP_HTTP_PORT=8080
rmcp serve-http

# Find and kill process using port
lsof -ti:8000 | xargs kill
```

### Permission Denied
**Issue**: Cannot write files or create directories

**Solutions**:
```bash
# Check current directory permissions
ls -la

# Create config directory if missing
mkdir -p ~/.rmcp

# Fix permissions
chmod 755 ~/.rmcp
```

## Runtime Issues

### Tool Call Failures
**Issue**: Statistical tools return errors

**Common causes and solutions**:

1. **Data format issues**:
   ```bash
   # Ensure data is properly formatted
   # CSV: comma-separated with headers
   # Array: [[1,2], [3,4]] format
   ```

2. **Missing required parameters**:
   ```bash
   # Check tool schema
   rmcp list-capabilities --tool linear_model
   ```

3. **R script errors**: Check error message for specific R issues

### Memory Issues
**Issue**: "Out of memory" or slow performance

**Solutions**:
```bash
# Increase R memory limit
export RMCP_R_MEMORY_LIMIT=4GB

# Use configuration file
echo '{"r": {"memory_limit": "4GB"}}' > ~/.rmcp/config.json

# For large datasets, consider data sampling
```

### Timeout Issues
**Issue**: "Timeout waiting for R process"

**Solutions**:
```bash
# Increase timeout
export RMCP_R_TIMEOUT=300

# Via configuration
echo '{"r": {"timeout": 300}}' > ~/.rmcp/config.json
```

## HTTP Server Issues

### CORS Errors
**Issue**: Browser blocks requests due to CORS

**Solution**:
```bash
# Allow all origins (development only)
export RMCP_CORS_ORIGINS="*"

# Production: specify allowed origins
export RMCP_CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

### Session Issues
**Issue**: "Session not found" or session expires

**Solution**:
- Sessions auto-expire after inactivity
- Re-initialize with `initialize` method
- Check session ID in response headers

## Claude Desktop Integration

### MCP Connection Issues
**Issue**: Claude Desktop doesn't find RMCP

**Common solutions**:

1. **Check Claude Desktop config**:
   ```json
   {
     "mcpServers": {
       "rmcp": {
         "command": "rmcp",
         "args": ["start"]
       }
     }
   }
   ```

2. **Verify RMCP is in PATH**:
   ```bash
   which rmcp
   rmcp --version
   ```

3. **Use full path**:
   ```json
   {
     "mcpServers": {
       "rmcp": {
         "command": "/full/path/to/rmcp",
         "args": ["start"]
       }
     }
   }
   ```

### Tool Discovery Issues
**Issue**: Claude Desktop shows "No tools available"

**Solutions**:
1. Check RMCP logs: `rmcp start --debug`
2. Verify tool registration: `rmcp list-capabilities`
3. Restart Claude Desktop after configuration changes

## Data Issues

### File Reading Errors
**Issue**: Cannot read CSV/Excel files

**Solutions**:
```bash
# Check file permissions
ls -la yourfile.csv

# Verify file format
head yourfile.csv

# Use absolute paths
rmcp read-csv /full/path/to/file.csv

# Check encoding (especially for international data)
file -I yourfile.csv
```

### Large Dataset Issues
**Issue**: Performance problems with large datasets

**Solutions**:
1. **Sample data**: Use representative subset
2. **Chunked processing**: Process data in smaller pieces
3. **Optimize queries**: Filter data before analysis
4. **Use Docker**: Better resource management

## Debugging

### Enable Debug Mode
```bash
# CLI debug mode
rmcp start --debug

# Environment variable
export RMCP_LOG_LEVEL=DEBUG
rmcp start

# Configuration file
echo '{"debug": true, "logging": {"level": "DEBUG"}}' > ~/.rmcp/config.json
```

### Check Logs
```bash
# View recent logs
tail -f ~/.rmcp/logs/rmcp.log

# Check system logs (Linux)
journalctl -u rmcp

# Docker logs
docker logs <container-id>
```

### Validate Configuration
```bash
# Check configuration loading
rmcp config show

# Validate config file
rmcp config validate ~/.rmcp/config.json

# Test connectivity
rmcp health-check
```

## Getting Help

### Check System Status
```bash
# Overall system check
rmcp diagnose

# List capabilities
rmcp list-capabilities

# Test specific tool
rmcp test-tool linear_model

# Check R integration
rmcp check-r
```

### Common Error Messages

**"Module not found: rmcp"**
- RMCP not installed: `pip install rmcp`
- Wrong Python environment: Check virtual environment

**"R script execution failed"**
- Check R installation with Docker approach
- Verify data format matches expected schema

**"Connection refused"**
- HTTP server not running: `rmcp serve-http`
- Wrong port/host configuration

**"Permission denied"**
- File permissions issue: Check file/directory access
- Config directory: Create `~/.rmcp/` if missing

### Still Need Help?
- **GitHub Issues**: [Report bugs and feature requests](https://github.com/finite-sample/rmcp/issues)
- **Documentation**: Complete API reference available
- **Examples**: Check working examples in `examples/` folder
