#!/bin/bash
set -e

# Detect if running in Cloud Run or similar environment
if [ -n "$PORT" ]; then
    echo "PORT environment variable detected: $PORT"
    echo "Starting RMCP in HTTP mode for Cloud Run..."
    exec rmcp serve-http --host 0.0.0.0 --port "$PORT"
elif [ "$1" = "rmcp" ]; then
    # Pass through rmcp commands
    exec "$@"
else
    # Default to stdio mode for MCP protocol
    exec rmcp start
fi