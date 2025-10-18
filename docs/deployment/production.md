# Production Deployment Guide

This guide covers deploying RMCP in production environments with optimized Docker images, security best practices, and scalability considerations.

## Production Docker Build

RMCP includes a multi-stage production Dockerfile optimized for minimal image size and security:

```bash
# Build production image (optimized, multi-stage)
docker build -f docker/Dockerfile --target production -t rmcp-production .

# Run production server
docker run -p 8000:8000 rmcp-production rmcp http
```

### Multi-Stage Optimization

The production Dockerfile uses a two-stage build:

1. **Builder Stage**: Installs build dependencies, compiles packages, installs R libraries
2. **Runtime Stage**: Minimal runtime environment with only necessary dependencies

Benefits:
- **Smaller Image Size**: ~50% reduction compared to development image
- **Faster Startup**: Optimized Python virtual environment
- **Security**: Non-root user, minimal attack surface
- **Performance**: Pre-compiled packages, optimized layers

## Security Features

### Non-Root User
Production containers run as user `rmcp` (not root):

```bash
# Verify security
docker run --rm rmcp-production whoami
# Output: rmcp
```

### Health Checks
Built-in health monitoring:

```bash
# Health check endpoint (HTTP mode)
curl http://localhost:8000/health

# Container health status
docker ps --filter "health=healthy"
```

### Resource Limits
Recommended production limits:

```bash
docker run \
  --memory=2g \
  --cpus=1.0 \
  --read-only \
  --tmpfs /tmp \
  -p 8000:8000 \
  rmcp-production rmcp http
```

## Deployment Modes

### 1. HTTP Server (Recommended)
For AI assistant integration via HTTP:

```bash
docker run -d \
  --name rmcp-server \
  --restart unless-stopped \
  -p 8000:8000 \
  rmcp-production rmcp http
```

### 2. Claude Desktop Integration
For local Claude Desktop integration:

```bash
# Start in stdio mode
docker run -i \
  --name rmcp-claude \
  rmcp-production rmcp start
```

### 3. High Availability Setup
For production load:

```bash
# Run multiple instances behind load balancer
for i in {1..3}; do
  docker run -d \
    --name rmcp-server-$i \
    -p $((8000+i)):8000 \
    rmcp-production rmcp http
done
```

## Performance and Scalability

### Concurrent Request Handling
RMCP handles concurrent requests efficiently:

- **HTTP Transport**: Async FastAPI with uvicorn
- **R Session Isolation**: Independent R processes per request
- **Memory Management**: Automatic cleanup after tool execution
- **Load Testing**: Validated with 10+ concurrent requests

### Performance Characteristics
Typical response times (tested on amd64/arm64):

- **Simple Statistics**: 100-300ms
- **Complex Models**: 500-2000ms  
- **Data Import/Export**: 200-1000ms
- **Visualization**: 300-800ms

### Resource Requirements

**Minimum (Development)**:
- CPU: 1 core
- Memory: 1GB RAM
- Storage: 2GB

**Recommended (Production)**:
- CPU: 2-4 cores
- Memory: 4-8GB RAM
- Storage: 10GB

**High Load (Enterprise)**:
- CPU: 8+ cores
- Memory: 16GB+ RAM
- Storage: 50GB+ SSD

## Multi-Platform Support

### Supported Architectures
- **amd64** (Intel/AMD x86_64)
- **arm64** (Apple Silicon, ARM servers)

### Building for Multiple Platforms

```bash
# Enable buildx
docker buildx create --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f docker/Dockerfile \
  --target production \
  -t rmcp-production:latest \
  --push .
```

### Platform-Specific Optimizations
- **R packages**: Compiled for target architecture
- **Numerical libraries**: Platform-optimized BLAS/LAPACK
- **Performance**: Architecture-specific optimizations

## Monitoring and Observability

### Health Monitoring
```bash
# Basic health check
curl -f http://localhost:8000/health || exit 1

# Detailed server status
curl http://localhost:8000/mcp -d '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "server/capabilities"
}'
```

### Logging
Configure log levels:

```bash
docker run \
  -e RMCP_LOG_LEVEL=INFO \
  -p 8000:8000 \
  rmcp-production rmcp http
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### Metrics Collection
Monitor key metrics:

- Request latency
- R session usage
- Memory consumption
- Error rates
- Tool execution times

## Troubleshooting

### Common Issues

**Container fails to start**:
```bash
# Check logs
docker logs rmcp-server

# Test with interactive mode
docker run -it rmcp-production bash
```

**R packages missing**:
```bash
# Verify R environment
docker exec rmcp-server R -e "installed.packages()[,1]"
```

**Performance issues**:
```bash
# Monitor resource usage
docker stats rmcp-server

# Check concurrent request handling
docker exec rmcp-server netstat -an | grep :8000
```

### Debug Mode
Run with detailed debugging:

```bash
docker run \
  -e RMCP_LOG_LEVEL=DEBUG \
  -p 8000:8000 \
  rmcp-production rmcp http
```

## Security Best Practices

1. **Network Security**: Use HTTPS in production
2. **Access Control**: Implement authentication/authorization
3. **Resource Limits**: Set memory/CPU constraints
4. **Read-Only Filesystem**: Mount volumes as read-only when possible
5. **Regular Updates**: Keep base images and R packages updated
6. **Secrets Management**: Use Docker secrets for sensitive data

## Production Checklist

- [ ] Built with production Dockerfile
- [ ] Running as non-root user
- [ ] Resource limits configured
- [ ] Health checks enabled
- [ ] Logging configured
- [ ] Monitoring in place
- [ ] Backup strategy defined
- [ ] Update process documented
- [ ] Security review completed
- [ ] Load testing performed

For additional support, see the troubleshooting documentation or open an issue on GitHub.