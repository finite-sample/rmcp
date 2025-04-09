import logging
from typing import Any, Callable, Dict

class Server:
    """
    A flexible server class for registering and executing tools.

    Attributes:
        tools (Dict[str, Callable]): A dictionary of registered tools.
    """
    def __init__(self):
        """
        Initialize the server with an empty tools dictionary.
        Sets up logging for tool-related operations.
        """
        self.tools: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)

    def register_tool(self, name: str, func: Callable):
        """
        Register a tool with the server.

        Args:
            name (str): The name of the tool.
            func (Callable): The function to be executed when the tool is called.

        Raises:
            ValueError: If a tool with the same name already exists.
        """
        if name in self.tools:
            self.logger.warning(f"Overwriting existing tool: {name}")
        
        self.tools[name] = func
        self.logger.info(f"Registered tool: {name}")

    def process_message(self, message: Dict[str, Any]) -> Any:
        """
        Process an incoming message by executing the specified tool.

        Args:
            message (Dict[str, Any]): A dictionary containing tool name and arguments.
                Expected keys:
                - 'tool': Name of the tool to execute
                - 'args': Dictionary of arguments for the tool (optional)

        Returns:
            The result of the tool execution.

        Raises:
            ValueError: If the specified tool is not found.
            TypeError: If arguments are invalid for the tool.
        """
        tool_name = message.get("tool")
        args = message.get("args", {})

        if not tool_name:
            raise ValueError("No tool specified in the message")

        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        try:
            func = self.tools[tool_name]
            return func(**args)
        except TypeError as e:
            self.logger.error(f"Error executing tool {tool_name}: {e}")
            raise TypeError(f"Invalid arguments for tool '{tool_name}': {e}")

    def list_tools(self) -> Dict[str, Callable]:
        """
        Retrieve the list of registered tools.

        Returns:
            Dict[str, Callable]: A dictionary of registered tools.
        """
        return self.tools.copy()