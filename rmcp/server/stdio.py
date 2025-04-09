# rmcp/server/stdio.py

import sys
import logging

def stdio_server(server):
    """
    Launch the MCP server using standard I/O (stdin/stdout).
    Should be passed an MCP-compatible server instance (e.g., FastMCP).
    """
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("rmcp-mcp")

    try:
        logger.debug("Starting MCP stdio server...")
        server.run()
    except Exception as e:
        logger.exception("Fatal error running MCP server")
        raise
