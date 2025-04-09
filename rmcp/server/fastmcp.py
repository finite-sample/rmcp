#!/usr/bin/env python3
import sys
import os
import json
import logging
import select
import time
from typing import Dict, Any, List, Optional, Union

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   stream=sys.stderr,
                   format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("rmcp-mcp")

class FastMCP:
    def __init__(self, name=None, version=None, description=None):
        """
        Initialize the FastMCP server.
        
        Args:
            name (str, optional): Name of the server
            version (str, optional): Version of the server
            description (str, optional): Description of the server
        """
        self.name = name
        self.version = version
        self.description = description
        self.tools = {}

    def tool(self, name=None, description=None, input_schema=None, schema=None, **kwargs):
        """
        Decorator to register a tool with optional metadata.
        
        Args:
            name (str, optional): Name of the tool. Defaults to function name.
            description (str, optional): Description of the tool.
            input_schema (dict, optional): JSON schema for input validation.
            schema (dict, optional): Alternative name for input_schema.
            **kwargs: Additional keyword arguments
        """
        def decorator(func):
            # Determine tool name
            tool_name = name or func.__name__
            
            # Prefer input_schema, fallback to schema
            tool_schema = input_schema or schema or {"type": "object", "properties": {}}
            
            # Register the tool with additional metadata
            self.register_tool(
                name=tool_name, 
                func=func, 
                description=description or "",
                schema=tool_schema
            )
            return func
        return decorator

    def register_tool(self, name, func, description="", schema=None):
        """
        Register a tool with optional metadata.
        
        Args:
            name (str): Name of the tool
            func (callable): The tool function
            description (str, optional): Description of the tool
            schema (dict, optional): JSON schema for input validation
        """
        # Use default empty schema if none provided
        if schema is None:
            schema = {"type": "object", "properties": {}}
        
        # Store tool with additional metadata
        self.tools[name] = {
            "function": func,
            "description": description,
            "schema": schema
        }
    
    def run(self):
        """Run the server, reading from stdin and writing to stdout"""
        logger.debug("Starting MCP server")
        
        # Properly handle stdin/stdout in binary mode
        stdin = os.fdopen(sys.stdin.fileno(), 'rb')
        stdout = os.fdopen(sys.stdout.fileno(), 'wb')
        
        # Message buffer and state
        buffer = b""
        content_length = None
        
        # Main loop
        while True:
            # Check if stdin is ready to read
            ready, _, _ = select.select([stdin], [], [], 0.1)
            
            if stdin in ready:
                # Read available data
                chunk = stdin.read(4096)
                if not chunk:
                    logger.debug("End of input stream, exiting")
                    break
                
                buffer += chunk
                
                # Process complete messages
                while True:
                    # If we don't know the content length yet, look for the header
                    if content_length is None:
                        header_end = buffer.find(b'\r\n\r\n')
                        if header_end == -1:
                            # Header not complete yet
                            break
                            
                        # Parse headers
                        header = buffer[:header_end].decode('utf-8')
                        logger.debug(f"Received header: {header}")
                        
                        for line in header.split('\r\n'):
                            if line.startswith('Content-Length: '):
                                content_length = int(line[16:])
                                logger.debug(f"Content length: {content_length}")
                                
                        # Remove header from buffer
                        buffer = buffer[header_end + 4:]  # +4 for '\r\n\r\n'
                    
                    # If we have the content length, check if we have enough data
                    if content_length is not None:
                        if len(buffer) >= content_length:
                            # We have a complete message
                            content = buffer[:content_length].decode('utf-8')
                            buffer = buffer[content_length:]
                            content_length = None
                            
                            # Process the message
                            try:
                                message = json.loads(content)
                                logger.debug(f"Received message: {message}")
                                
                                response = self.process_message(message)
                                if response:
                                    self.send_response(stdout, response)
                            except json.JSONDecodeError:
                                logger.error(f"Invalid JSON: {content}")
                            except Exception as e:
                                logger.error(f"Error processing message: {e}")
                                import traceback
                                logger.error(traceback.format_exc())
                        else:
                            # Need more data
                            break
                    else:
                        # No content length found
                        break
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.01)
            
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