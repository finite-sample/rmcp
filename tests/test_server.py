"""
Tests for RMCP server components.
"""

import pytest
import json
import io
from unittest.mock import patch, MagicMock
from rmcp.server.legacy_server import legacy_server
from rmcp.server.fastmcp import FastMCP
from rmcp.tools import mcp


class TestLegacyServer:
    """Test legacy server functionality."""
    
    def test_successful_tool_call(self):
        """Test successful tool execution via legacy server."""
        # Mock stdin with a simple tool call
        test_input = json.dumps({
            "tool": "correlation",
            "args": {
                "data": {"x": [1, 2, 3], "y": [2, 4, 6]},
                "var1": "x", 
                "var2": "y",
                "method": "pearson"
            }
        })
        
        with patch('sys.stdin', io.StringIO(test_input)):
            with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
                legacy_server(mcp)
                output = mock_stdout.getvalue()
                
                # Should return JSON result
                result = json.loads(output)
                assert "correlation" in result
                assert result["correlation"] == 1.0  # Perfect correlation
    
    def test_invalid_json_input(self):
        """Test handling of invalid JSON input."""
        test_input = "{ invalid json"
        
        with patch('sys.stdin', io.StringIO(test_input)):
            with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
                legacy_server(mcp)
                output = mock_stdout.getvalue()
                
                result = json.loads(output)
                assert "error" in result
                assert "Invalid JSON" in result["error"]
    
    def test_missing_tool_field(self):
        """Test handling of request without tool field."""
        test_input = json.dumps({"args": {"some": "data"}})
        
        with patch('sys.stdin', io.StringIO(test_input)):
            with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
                legacy_server(mcp)
                output = mock_stdout.getvalue()
                
                result = json.loads(output)
                assert "error" in result
                assert "Missing 'tool'" in result["error"]
    
    def test_unknown_tool(self):
        """Test handling of unknown tool request."""
        test_input = json.dumps({
            "tool": "unknown_tool",
            "args": {}
        })
        
        with patch('sys.stdin', io.StringIO(test_input)):
            with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
                legacy_server(mcp)
                output = mock_stdout.getvalue()
                
                result = json.loads(output)
                assert "error" in result
                assert "Unknown tool" in result["error"]
    
    def test_tool_execution_error(self):
        """Test handling of tool execution errors."""
        test_input = json.dumps({
            "tool": "linear_model",
            "args": {
                "formula": "invalid ~ formula ~ syntax",
                "data": {"x": [1, 2, 3]}
            }
        })
        
        with patch('sys.stdin', io.StringIO(test_input)):
            with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
                legacy_server(mcp)
                output = mock_stdout.getvalue()
                
                result = json.loads(output)
                assert "error" in result
                assert "Tool execution failed" in result["error"]
    
    def test_empty_input(self):
        """Test handling of empty input."""
        with patch('sys.stdin', io.StringIO("")):
            with patch('sys.stdout', new=io.StringIO()) as mock_stdout:
                legacy_server(mcp)
                # Should handle gracefully without output
                output = mock_stdout.getvalue()
                assert output == "" or output.isspace()


class TestFastMCP:
    """Test FastMCP server functionality."""
    
    def test_server_creation(self):
        """Test creating FastMCP server instance."""
        server = FastMCP(
            name="Test Server",
            version="1.0.0", 
            description="Test server description"
        )
        
        assert server.name == "Test Server"
        assert server.version == "1.0.0"
        assert server.description == "Test server description"
        assert server.tools == {}
    
    def test_tool_registration(self):
        """Test tool registration."""
        server = FastMCP("Test", "1.0", "Test server")
        
        def test_tool(arg1: str, arg2: int = 10) -> dict:
            return {"result": f"{arg1}_{arg2}"}
        
        server.register_tool(
            name="test_tool",
            func=test_tool,
            description="A test tool",
            schema={"type": "object", "properties": {"arg1": {"type": "string"}}}
        )
        
        assert "test_tool" in server.tools
        assert server.tools["test_tool"]["function"] == test_tool
        assert server.tools["test_tool"]["description"] == "A test tool"
        assert "properties" in server.tools["test_tool"]["schema"]
    
    def test_tool_decorator(self):
        """Test tool registration via decorator."""
        server = FastMCP("Test", "1.0", "Test server")
        
        @server.tool(
            name="decorated_tool",
            description="Decorated tool",
            input_schema={"type": "object"}
        )
        def decorated_tool(value: int) -> dict:
            return {"doubled": value * 2}
        
        assert "decorated_tool" in server.tools
        assert server.tools["decorated_tool"]["function"] == decorated_tool
    
    def test_initialize_message(self):
        """Test handling of initialize message."""
        server = FastMCP("Test Server", "1.0.0", "Test description")
        
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        
        response = server.process_message(message)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["server"]["name"] == "Test Server"
        assert response["result"]["server"]["version"] == "1.0.0"
    
    def test_get_capabilities_message(self):
        """Test handling of getCapabilities message."""
        server = FastMCP("Test Server", "1.0.0", "Test description")
        
        # Register a test tool
        server.register_tool(
            name="test_tool",
            func=lambda: {},
            description="Test tool",
            schema={"type": "object"}
        )
        
        message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "getCapabilities"
        }
        
        response = server.process_message(message)
        
        assert response["jsonrpc"] == "2.0" 
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 1
        assert response["result"]["tools"][0]["name"] == "test_tool"
    
    def test_tool_call_message(self):
        """Test handling of toolCall message."""
        server = FastMCP("Test Server", "1.0.0", "Test description")
        
        # Register a test tool
        def multiply_tool(x: int, y: int) -> dict:
            return {"result": x * y}
        
        server.register_tool(
            name="multiply",
            func=multiply_tool,
            schema={"type": "object"}
        )
        
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "toolCall",
            "params": {
                "name": "multiply",
                "arguments": {"x": 6, "y": 7}
            }
        }
        
        response = server.process_message(message)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        assert response["result"]["output"]["result"] == 42
    
    def test_unknown_tool_call(self):
        """Test calling unknown tool."""
        server = FastMCP("Test Server", "1.0.0", "Test description")
        
        message = {
            "jsonrpc": "2.0", 
            "id": 4,
            "method": "toolCall",
            "params": {
                "name": "unknown_tool",
                "arguments": {}
            }
        }
        
        response = server.process_message(message)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "Unknown tool" in response["error"]["message"]
    
    def test_tool_execution_error(self):
        """Test tool execution error handling."""
        server = FastMCP("Test Server", "1.0.0", "Test description")
        
        def error_tool() -> dict:
            raise ValueError("Tool execution failed")
        
        server.register_tool("error_tool", error_tool, schema={"type": "object"})
        
        message = {
            "jsonrpc": "2.0",
            "id": 5, 
            "method": "toolCall",
            "params": {
                "name": "error_tool",
                "arguments": {}
            }
        }
        
        response = server.process_message(message)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 5
        assert "error" in response
        assert response["error"]["code"] == -32603
    
    def test_unknown_method(self):
        """Test handling of unknown method."""
        server = FastMCP("Test Server", "1.0.0", "Test description")
        
        message = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "unknownMethod"
        }
        
        response = server.process_message(message)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 6
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]
    
    def test_shutdown_message(self):
        """Test handling of shutdown message."""
        server = FastMCP("Test Server", "1.0.0", "Test description")
        
        message = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "shutdown"
        }
        
        response = server.process_message(message)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 7
        assert "result" in response
        assert response["result"] is None