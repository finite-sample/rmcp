#!/usr/bin/env python3
import sys
import os
import json
import logging
from typing import Dict, Any, List, Optional, Union

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   stream=sys.stderr,
                   format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("rmcp-mcp")

class MCPServer:
    def __init__(self, name: str, version: str, description: str):
        self.name = name
        self.version = version
        self.description = description
        self.tools = {}
        self.next_id = 1
        
    def register_tool(self, name: str, func, description: str = "", schema: Dict = None):
        """Register a tool with the server"""
        if schema is None:
            # Create a basic schema if none provided
            schema = {"type": "object", "properties": {}}
            
        self.tools[name] = {
            "function": func,
            "description": description,
            "schema": schema
        }
        logger.debug(f"Registered tool: {name}")
        
    def tool(self, name: str = None, description: str = "", schema: Dict = None):
        """Decorator to register a tool"""
        def decorator(func):
            tool_name = name if name else func.__name__
            self.register_tool(tool_name, func, description, schema)
            return func
        return decorator
    
    def run(self):
        """Run the server, reading from stdin and writing to stdout"""
        logger.debug("Starting MCP server")
        
        # Use binary mode for stdin/stdout to avoid encoding issues
        stdin = os.fdopen(sys.stdin.fileno(), 'rb')
        stdout = os.fdopen(sys.stdout.fileno(), 'wb')
        
        # Process messages in a loop
        while True:
            try:
                # Read the message header
                header = stdin.readline().decode('utf-8').strip()
                if not header:
                    logger.debug("Empty header received, exiting")
                    break
                    
                # Parse message length
                if not header.startswith("Content-Length: "):
                    logger.error(f"Invalid header: {header}")
                    continue
                    
                content_length = int(header.split(": ")[1])
                
                # Skip the empty line after the header
                stdin.readline()
                
                # Read the message content
                content = stdin.read(content_length).decode('utf-8')
                message = json.loads(content)
                logger.debug(f"Received message: {message}")
                
                # Process the message and send a response
                response = self.process_message(message)
                if response:
                    self.send_response(stdout, response)
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                import traceback
                logger.error(traceback.format_exc())
                break
                
        logger.debug("Server shutting down")
    
    def send_response(self, stdout, response):
        """Send a response message over stdout"""
        response_json = json.dumps(response)
        response_bytes = response_json.encode('utf-8')
        
        header = f"Content-Length: {len(response_bytes)}\r\n\r\n"
        stdout.write(header.encode('utf-8'))
        stdout.write(response_bytes)
        stdout.flush()
        
        logger.debug(f"Sent response: {response}")
    
    def process_message(self, message):
        """Process an incoming JSON-RPC message"""
        method = message.get("method")
        params = message.get("params", {})
        message_id = message.get("id")
        
        logger.debug(f"Processing method: {method} with ID: {message_id}")
        
        # Handle initialize method
        if method == "initialize":
            return self.handle_initialize(params, message_id)
        
        # Handle shutdown method
        elif method == "shutdown":
            logger.debug("Shutdown requested")
            return {"jsonrpc": "2.0", "result": None, "id": message_id}
        
        # Handle getCapabilities method
        elif method == "getCapabilities":
            return self.handle_get_capabilities(message_id)
            
        # Handle toolCall method
        elif method == "toolCall":
            return self.handle_tool_call(params, message_id)
            
        # Handle unknown methods
        else:
            logger.warning(f"Unknown method: {method}")
            return {
                "jsonrpc": "2.0", 
                "error": {"code": -32601, "message": f"Method not found: {method}"}, 
                "id": message_id
            }
    
    def handle_initialize(self, params, message_id):
        """Handle the initialize method"""
        logger.debug("Handling initialize")
        
        # Store client capabilities if needed
        client_capabilities = params.get("capabilities", {})
        client_info = params.get("clientInfo", {})
        
        logger.debug(f"Client info: {client_info}")
        logger.debug(f"Client capabilities: {client_capabilities}")
        
        # Return server information
        return {
            "jsonrpc": "2.0",
            "result": {
                "server": {
                    "name": self.name,
                    "version": self.version,
                },
                "capabilities": {
                    "tools": len(self.tools) > 0
                }
            },
            "id": message_id
        }
    
    def handle_get_capabilities(self, message_id):
        """Handle the getCapabilities method"""
        logger.debug("Handling getCapabilities")
        
        # Format tools for the MCP protocol
        tool_capabilities = []
        
        for name, tool_info in self.tools.items():
            tool_capabilities.append({
                "name": name,
                "description": tool_info["description"],
                "inputSchema": tool_info["schema"]
            })
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": tool_capabilities
            },
            "id": message_id
        }
    
    def handle_tool_call(self, params, message_id):
        """Handle the toolCall method"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        logger.debug(f"Tool call: {tool_name} with arguments: {arguments}")
        
        if tool_name not in self.tools:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": f"Unknown tool: {tool_name}"
                },
                "id": message_id
            }
        
        try:
            # Call the tool function with the provided arguments
            result = self.tools[tool_name]["function"](**arguments)
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "output": result
                },
                "id": message_id
            }
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Error executing tool {tool_name}: {str(e)}"
                },
                "id": message_id
            }

# Example use
if __name__ == "__main__":
    # Import your original tools here
    try:
        sys.path.insert(0, "/Users/soodoku/Documents/GitHub")
        from rmcp.tools import regression, diagnostics
        
        # Create server
        server = MCPServer(
            name="RMCP Server",
            version="1.0.0",
            description="R-based Model Completion Protocol server"
        )
        
        # Register your existing tools
        @server.tool(name="linear_model", description="Run a linear regression model", 
                    schema={"type": "object", "properties": {
                        "formula": {"type": "string", "description": "R formula expression"},
                        "data": {"type": "object", "description": "Data for the model"},
                        "robust": {"type": "boolean", "description": "Use robust standard errors"}
                    }})
        def linear_model(formula, data, robust=False):
            return regression.linear_model(formula, data, robust)
        
        @server.tool(name="diagnostics", description="Run regression diagnostics",
                   schema={"type": "object", "properties": {
                       "data": {"type": "object", "description": "Model data"},
                       "model": {"type": "object", "description": "Model object"}
                   }})
        def run_diagnostics(data, model):
            return diagnostics.run_diagnostics(data, model)
        
        # Run the server
        logger.debug("Starting RMCP MCP server")
        server.run()
        
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        import traceback
        logger.error(traceback.format_exc())