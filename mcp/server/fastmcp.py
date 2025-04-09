# mcp/server/fastmcp.py

from . import Server

class FastMCP(Server):
    def __init__(self, name, version, description):
        super().__init__()
        self.name = name
        self.version = version
        self.description = description

    def tool(self, name=None, description="", input_schema=None):
        """
        Decorator to register a tool. The decorated function will
        be callable through the MCP message protocol.
        """
        def decorator(func):
            tool_name = name if name else func.__name__
            self.register_tool(tool_name, func)
            return func
        return decorator

    def resource(self, name):
        """
        Decorator to register a resource.
        """
        def decorator(func):
            self.register_tool(name, func)
            return func
        return decorator

    def prompt(self, name):
        """
        Decorator to register a prompt.
        """
        def decorator(func):
            self.register_tool(name, func)
            return func
        return decorator
