# mcp/server/__init__.py

class Server:
    """
    A basic server class that holds registered tools.
    """
    def __init__(self):
        self.tools = {}

    def register_tool(self, name, func):
        self.tools[name] = func

    def process_message(self, message):
        """
        Process an incoming message by matching a tool name.
        The message should be a dict with 'tool' and 'args' keys.
        """
        tool_name = message.get("tool")
        args = message.get("args", {})
        if tool_name in self.tools:
            func = self.tools[tool_name]
            return func(**args)
        else:
            raise ValueError(f"Tool '{tool_name}' not found.")
