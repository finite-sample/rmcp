#!/usr/bin/env python3
"""
Legacy server mode that handles simple JSON tool calls for backward compatibility.
This allows the existing tests to work while maintaining MCP protocol support.
"""
import sys
import json
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                   stream=sys.stderr,
                   format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("rmcp-legacy")

def legacy_server(mcp_instance):
    """
    Run server in legacy mode - accepts simple JSON tool calls from stdin.
    Format: {"tool": "tool_name", "args": {...}}
    """
    logger.debug("Starting legacy server mode")
    
    try:
        # Read input from stdin
        input_line = sys.stdin.read().strip()
        if not input_line:
            logger.debug("No input received")
            return
            
        logger.debug(f"Received input: {input_line}")
        
        # Parse the JSON request
        try:
            request = json.loads(input_line)
        except json.JSONDecodeError as e:
            error_response = {"error": f"Invalid JSON: {str(e)}"}
            print(json.dumps(error_response))
            return
        
        # Extract tool name and arguments
        tool_name = request.get("tool")
        args = request.get("args", {})
        
        if not tool_name:
            error_response = {"error": "Missing 'tool' field in request"}
            print(json.dumps(error_response))
            return
        
        logger.debug(f"Tool call: {tool_name} with args: {args}")
        
        # Check if tool exists
        if tool_name not in mcp_instance.tools:
            error_response = {"error": f"Unknown tool: {tool_name}"}
            print(json.dumps(error_response))
            return
        
        # Execute the tool
        try:
            result = mcp_instance.tools[tool_name]["function"](**args)
            print(json.dumps(result))
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            error_response = {"error": f"Tool execution failed: {str(e)}"}
            print(json.dumps(error_response))
            
    except Exception as e:
        logger.error(f"Legacy server error: {e}")
        error_response = {"error": f"Server error: {str(e)}"}
        print(json.dumps(error_response))