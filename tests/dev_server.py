# dev_server.py
from rmcp.tools import mcp, execute_r_script
from rmcp.server.stdio import stdio_server

# If there is any additional server configuration, add it here

if __name__ == "__main__":
    # Launch the MCP server using standard input
    stdio_server(mcp)
