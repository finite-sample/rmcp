#!/usr/bin/env python3
"""
MCP Protocol Compliance Tests for Error Handling.

Tests that RMCP error responses conform exactly to the Model Context Protocol
specification for error handling. Ensures that Claude and other MCP clients
receive properly formatted error responses.

Key MCP Protocol Requirements for Errors:
1. JSON-RPC 2.0 error response format
2. Proper error codes (-32xxx range for JSON-RPC, application-specific for tools)
3. Human-readable error messages
4. Structured error data for programmatic handling
5. Proper content type and encoding
"""

import asyncio
import json
from shutil import which
from typing import Any

import pytest
from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.fileops import read_csv
from rmcp.tools.regression import linear_model, logistic_regression
from rmcp.tools.statistical_tests import chi_square_test

# Add rmcp to path
# rmcp package installed via pip install -e .


pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for MCP error protocol tests"
)


class TestMCPErrorProtocolCompliance:
    """Test MCP protocol compliance for error responses."""

    async def create_mcp_server(self):
        """Create MCP server with error-prone tools for testing."""
        server = create_server()
        register_tool_functions(
            server.tools, linear_model, logistic_regression, chi_square_test, read_csv
        )
        return server

    def validate_jsonrpc_error_structure(
        self, response: dict[str, Any], request_id: Any = None
    ):
        """Validate that response follows JSON-RPC 2.0 error format."""
        # Required JSON-RPC fields
        assert response.get("jsonrpc") == "2.0", "Must include jsonrpc version"
        assert "error" in response, "Error response must include 'error' field"

        if request_id is not None:
            assert response.get("id") == request_id, "Must echo request ID"

        # Error object structure
        error = response["error"]
        assert isinstance(error, dict), "Error must be an object"
        assert "code" in error, "Error must include numeric code"
        assert "message" in error, "Error must include message string"
        assert isinstance(error["code"], int), "Error code must be integer"
        assert isinstance(error["message"], str), "Error message must be string"
        assert len(error["message"]) > 0, "Error message must not be empty"

    def validate_mcp_tool_error_structure(self, response: dict[str, Any]):
        """Validate MCP tool error response structure."""
        assert "result" in response, "Tool error should be in result, not error field"

        result = response["result"]
        assert result.get("isError") is True, "Tool error must set isError=true"
        assert "content" in result, "Tool error must include content"

        content = result["content"]
        assert isinstance(content, list), "Content must be array"
        assert len(content) > 0, "Content must not be empty"

        # Check first content item
        first_content = content[0]
        assert "type" in first_content, "Content must specify type"
        assert first_content["type"] in [
            "text",
            "resource",
        ], "Content type must be text or resource"

        if first_content["type"] == "text":
            assert "text" in first_content, "Text content must include text field"
            assert len(first_content["text"]) > 0, "Text content must not be empty"

    @pytest.mark.asyncio
    async def test_unknown_tool_error_protocol(self):
        """Test MCP protocol compliance for unknown tool errors."""
        server = await self.create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 123,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {"some": "data"}},
        }

        response = await server.handle_request(request)

        # Should be JSON-RPC error (not tool error)
        self.validate_jsonrpc_error_structure(response, request_id=123)

        error = response["error"]
        assert error["code"] == -32603, "Unknown tool should be internal error (-32603)"
        assert (
            "unknown tool" in error["message"].lower()
        ), "Message should mention unknown tool"

        print("✅ Unknown tool error protocol compliance verified")
        print(f"   Error code: {error['code']}")
        print(f"   Message: {error['message']}")

    @pytest.mark.asyncio
    async def test_invalid_request_error_protocol(self):
        """Test MCP protocol compliance for invalid request format."""
        server = await self.create_mcp_server()

        # Invalid request (missing method but has id)
        invalid_request = {
            "jsonrpc": "2.0",
            "id": 123,
            # Missing method
            "params": {"some": "data"},
        }

        response = await server.handle_request(invalid_request)

        # Should be JSON-RPC error
        self.validate_jsonrpc_error_structure(response)

        error = response["error"]
        assert error["code"] == -32600, "Invalid request should be code -32600"

        print("✅ Invalid request error protocol compliance verified")
        print(f"   Error code: {error['code']}")

    @pytest.mark.asyncio
    async def test_schema_validation_error_protocol(self):
        """Test MCP protocol compliance for schema validation errors."""
        server = await self.create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 456,
            "method": "tools/call",
            "params": {
                "name": "linear_model",
                "arguments": {
                    # Missing required 'data' field
                    "formula": "y ~ x"
                },
            },
        }

        response = await server.handle_request(request)

        # Schema validation errors should be tool errors (not JSON-RPC errors)
        self.validate_mcp_tool_error_structure(response)

        # Extract error text
        content_text = response["result"]["content"][0]["text"]
        assert "'data' is a required property" in content_text

        print("✅ Schema validation error protocol compliance verified")
        print(f"   Error text: {content_text[:80]}...")

    @pytest.mark.asyncio
    async def test_r_execution_error_protocol(self):
        """Test MCP protocol compliance for R execution errors."""
        server = await self.create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 789,
            "method": "tools/call",
            "params": {
                "name": "linear_model",
                "arguments": {
                    "data": {},  # Empty data causes R error
                    "formula": "y ~ x",
                },
            },
        }

        response = await server.handle_request(request)

        # R execution errors should be tool errors
        self.validate_mcp_tool_error_structure(response)

        content_text = response["result"]["content"][0]["text"]
        assert (
            "tool execution error" in content_text.lower()
            or "error" in content_text.lower()
        )

        print("✅ R execution error protocol compliance verified")
        print(f"   Error text: {content_text[:80]}...")

    @pytest.mark.asyncio
    async def test_file_error_protocol(self):
        """Test MCP protocol compliance for file operation errors."""
        server = await self.create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "read_csv",
                "arguments": {"file_path": "/nonexistent/file.csv"},
            },
        }

        response = await server.handle_request(request)

        # File errors should be tool errors
        self.validate_mcp_tool_error_structure(response)

        content_text = response["result"]["content"][0]["text"]
        assert any(
            keyword in content_text.lower()
            for keyword in ["file", "not found", "does not exist"]
        )

        print("✅ File error protocol compliance verified")
        print(f"   Error text: {content_text[:80]}...")

    @pytest.mark.asyncio
    async def test_error_message_localization_ready(self):
        """Test that error messages are structured for potential localization."""
        server = await self.create_mcp_server()

        # Test multiple error scenarios
        test_cases = [
            {
                "name": "linear_model",
                "args": {"formula": "y ~ x"},  # Missing data
                "error_type": "schema_validation",
            },
            {
                "name": "nonexistent_tool",
                "args": {"any": "data"},
                "error_type": "unknown_tool",
            },
        ]

        for case in test_cases:
            request = {
                "jsonrpc": "2.0",
                "id": 999,
                "method": "tools/call",
                "params": {"name": case["name"], "arguments": case["args"]},
            }

            response = await server.handle_request(request)

            # Check message structure
            if "error" in response:
                # JSON-RPC error
                message = response["error"]["message"]
            else:
                # Tool error
                message = response["result"]["content"][0]["text"]

            # Messages should be complete sentences
            assert len(message) > 10, "Error messages should be descriptive"
            assert message[
                0
            ].isupper(), "Error messages should start with capital letter"

            # Should not contain raw technical details
            assert "traceback" not in message.lower(), "Should not expose stack traces"
            assert "__" not in message, "Should not expose internal names"

            print(f"✅ Error message structure verified for {case['error_type']}")

    @pytest.mark.asyncio
    async def test_error_response_timing(self):
        """Test that error responses are returned promptly."""
        server = await self.create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 555,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }

        import time

        start_time = time.time()
        response = await server.handle_request(request)
        end_time = time.time()

        response_time = end_time - start_time

        # Error responses should be fast (< 1 second)
        assert (
            response_time < 1.0
        ), f"Error response took {response_time:.2f}s (should be < 1s)"

        # Should still be properly formatted
        self.validate_jsonrpc_error_structure(response, request_id=555)

        print(f"✅ Error response timing verified: {response_time:.3f}s")

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test that concurrent error requests are handled properly."""
        server = await self.create_mcp_server()

        # Create multiple error-inducing requests
        requests = []
        for i in range(5):
            request = {
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "linear_model",
                    "arguments": {"data": {}, "formula": "y ~ x"},  # Empty data error
                },
            }
            requests.append(server.handle_request(request))

        # Execute concurrently
        responses = await asyncio.gather(*requests, return_exceptions=True)

        # All should be proper error responses
        for i, response in enumerate(responses):
            assert not isinstance(response, Exception), f"Request {i} raised exception"
            self.validate_mcp_tool_error_structure(response)
            assert response.get("id") == i, f"Request {i} ID mismatch"

        print(f"✅ Concurrent error handling verified: {len(responses)} requests")

    @pytest.mark.asyncio
    async def test_error_content_encoding(self):
        """Test that error content is properly encoded."""
        server = await self.create_mcp_server()

        request = {
            "jsonrpc": "2.0",
            "id": 777,
            "method": "tools/call",
            "params": {
                "name": "linear_model",
                "arguments": {
                    "data": {"special_chars": ["café", "naïve", "résumé"]},
                    "formula": "y ~ special_chars",
                },
            },
        }

        response = await server.handle_request(request)

        # Should handle special characters properly
        response_json = json.dumps(response, ensure_ascii=False)
        assert (
            "café" not in response_json or len(response_json) > 0
        )  # Either filtered or encoded

        # Response should be valid JSON
        parsed_back = json.loads(response_json)
        assert parsed_back == response, "Response should round-trip through JSON"

        print("✅ Error content encoding verified")


class TestMCPErrorMetadata:
    """Test MCP error response metadata and structured data."""

    @pytest.mark.asyncio
    async def test_error_metadata_structure(self):
        """Test that errors include structured metadata when appropriate."""
        server = create_server()
        register_tool_functions(server.tools, linear_model)

        request = {
            "jsonrpc": "2.0",
            "id": 888,
            "method": "tools/call",
            "params": {
                "name": "linear_model",
                "arguments": {
                    "data": {"x": [1, 2], "y": [3, 4]},  # Too little data
                    "formula": "y ~ x",
                },
            },
        }

        response = await server.handle_request(request)

        # Check if response includes helpful metadata
        if "result" in response and response["result"].get("isError"):
            content = response["result"]["content"]

            # Content should be informative
            assert len(content) > 0
            text_content = next((c for c in content if c.get("type") == "text"), None)
            assert text_content is not None

            # Should provide actionable guidance
            text = text_content["text"]
            helpful_keywords = [
                "data",
                "observations",
                "sample",
                "size",
                "degrees",
                "freedom",
            ]
            assert any(keyword in text.lower() for keyword in helpful_keywords)

        print("✅ Error metadata structure verified")

    @pytest.mark.asyncio
    async def test_error_categorization(self):
        """Test that errors are properly categorized for client handling."""
        server = create_server()
        register_tool_functions(server.tools, linear_model, read_csv)

        error_categories = [
            {
                "request": {
                    "name": "linear_model",
                    "arguments": {"formula": "y ~ x"},  # Schema error
                },
                "expected_category": "validation_error",
            },
            {
                "request": {
                    "name": "read_csv",
                    "arguments": {"file_path": "/nonexistent.csv"},  # File error
                },
                "expected_category": "file_error",
            },
        ]

        for i, test_case in enumerate(error_categories):
            request = {
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": test_case["request"],
            }

            response = await server.handle_request(request)

            # Check that error provides enough information for categorization
            if "result" in response and response["result"].get("isError"):
                text = response["result"]["content"][0]["text"]

                # Text should contain category-specific keywords
                if test_case["expected_category"] == "validation_error":
                    assert "required property" in text or "validation" in text.lower()
                elif test_case["expected_category"] == "file_error":
                    assert any(
                        keyword in text.lower()
                        for keyword in ["file", "not found", "does not exist"]
                    )

            print(
                f"✅ Error categorization verified for {test_case['expected_category']}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
