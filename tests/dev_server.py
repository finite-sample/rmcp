# dev_server.py
from rmcp.tools import mcp
from rmcp.server.stdio import stdio_server
from rmcp.server.legacy_server import legacy_server
import sys
import io

def run_dev_server():
    """Run the development server in legacy mode for testing"""
    print("Running development server...")
    # For dev mode, default to legacy server for easier testing
    legacy_server(mcp)

# If there is any additional server configuration, add it here

if __name__ == "__main__":
    run_dev_server()
