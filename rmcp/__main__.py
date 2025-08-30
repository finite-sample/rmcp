from rmcp.tools import mcp
from rmcp.server.stdio import stdio_server
from rmcp.server.legacy_server import legacy_server
import sys
import select

def detect_input_mode():
    """
    Detect if input is MCP protocol (starts with Content-Length) or legacy JSON
    """
    if not sys.stdin.isatty():
        # Check if data is available to read
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        if ready:
            # Peek at first line without consuming it
            first_line = sys.stdin.readline()
            if first_line.startswith('Content-Length:'):
                # This looks like MCP protocol
                # We need to put the line back, but Python doesn't allow that easily
                # So we'll use a different approach - let MCP server handle it
                return "mcp"
            elif first_line.strip().startswith('{'):
                # This looks like JSON
                # Put the data back for legacy server to process
                import io
                sys.stdin = io.StringIO(first_line + sys.stdin.read())
                return "legacy"
    return "legacy"  # Default to legacy mode

def main():
    """Main entry point for rmcp when run as module."""
    mode = detect_input_mode()
    if mode == "mcp":
        stdio_server(mcp)
    else:
        legacy_server(mcp)

if __name__ == "__main__":
    main()

