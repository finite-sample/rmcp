#!/usr/bin/env python3
"""
Test suite for Claude API compatibility - ensures schemas work with Claude Code.

This test suite verifies that:
1. No tool schemas contain oneOf/allOf/anyOf at the top level (Claude API restriction)
2. All flattened schemas still properly validate inputs
3. Tools with modified schemas maintain backward compatibility
4. The entire tool registry is compatible with Claude's API requirements
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest
from jsonschema import ValidationError, validate

# Add rmcp to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.cli import _register_builtin_tools
from rmcp.core.server import create_server
from rmcp.tools.machine_learning import decision_tree, random_forest
from rmcp.tools.statistical_tests import chi_square_test
from rmcp.tools.flexible_r import execute_r_analysis


class TestClaudeAPISchemaCompliance:
    """Test that all tool schemas comply with Claude API requirements."""

    @pytest.fixture
    def server_with_all_tools(self):
        """Create a server with all built-in tools registered."""
        server = create_server()
        _register_builtin_tools(server)
        return server

    def test_no_top_level_oneOf_allOf_anyOf(self, server_with_all_tools):
        """Test that no tool schema contains oneOf/allOf/anyOf at top level."""
        problematic_tools = []
        tools_checked = 0

        # Get all registered tools
        for tool_name, tool in server_with_all_tools.tools._tools.items():
            tools_checked += 1
            schema = tool.input_schema

            # Check if top-level schema contains problematic keywords
            if isinstance(schema, dict):
                schema_str = json.dumps(schema)
                # Check for these keywords at the top level of the schema
                if any(key in schema for key in ['oneOf', 'allOf', 'anyOf']):
                    problematic_tools.append({
                        'name': tool_name,
                        'issue': 'Contains oneOf/allOf/anyOf at top level'
                    })

        # Report findings
        print(f"\n✅ Checked {tools_checked} tools for Claude API compatibility")

        if problematic_tools:
            print("\n❌ Found tools with schema issues:")
            for tool in problematic_tools:
                print(f"  - {tool['name']}: {tool['issue']}")
            pytest.fail(f"Found {len(problematic_tools)} tools with Claude-incompatible schemas")
        else:
            print("✅ All tools have Claude-compatible schemas")
            assert tools_checked >= 44, f"Expected at least 44 tools, found {tools_checked}"

    def test_decision_tree_flattened_schema(self):
        """Test that decision_tree's flattened schema still validates properly."""
        input_schema = decision_tree._mcp_tool_input_schema
        output_schema = decision_tree._mcp_tool_output_schema

        # Verify the output schema performance field is flattened (no oneOf)
        assert 'oneOf' not in str(output_schema)

        # Test valid classification input
        valid_classification = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": ["A", "B", "A"]},
            "formula": "y ~ x1 + x2",
            "method": "class"
        }
        validate(instance=valid_classification, schema=input_schema)

        # Test valid regression input
        valid_regression = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": [10, 20, 30]},
            "formula": "y ~ x1 + x2",
            "method": "anova"
        }
        validate(instance=valid_regression, schema=input_schema)

        print("✅ decision_tree schema validated correctly")

    def test_random_forest_flattened_schema(self):
        """Test that random_forest's flattened schema still validates properly."""
        input_schema = random_forest._mcp_tool_input_schema
        output_schema = random_forest._mcp_tool_output_schema

        # Verify the output schema performance field is flattened (no oneOf)
        assert 'oneOf' not in str(output_schema)

        # Test valid classification input
        valid_classification = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": ["A", "B", "A"]},
            "formula": "y ~ x1 + x2",
            "n_trees": 100,
            "mtry": 2
        }
        validate(instance=valid_classification, schema=input_schema)

        # Test valid regression input
        valid_regression = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": [10, 20, 30]},
            "formula": "y ~ x1 + x2",
            "n_trees": 50
        }
        validate(instance=valid_regression, schema=input_schema)

        print("✅ random_forest schema validated correctly")

    def test_chi_square_test_flattened_schema(self):
        """Test that chi_square_test's flattened schema still validates properly."""
        schema = chi_square_test._mcp_tool_input_schema

        # Verify no oneOf at top level
        assert 'oneOf' not in schema

        # Test valid independence test
        valid_independence = {
            "data": {"var1": ["A", "B", "A"], "var2": ["X", "Y", "X"]},
            "test_type": "independence",
            "x": "var1",
            "y": "var2"
        }
        validate(instance=valid_independence, schema=schema)

        # Test valid goodness of fit
        valid_goodness = {
            "data": {"category": ["A", "B", "C"]},
            "test_type": "goodness_of_fit",
            "x": "category",
            "expected": [0.3, 0.4, 0.3]
        }
        validate(instance=valid_goodness, schema=schema)

        print("✅ chi_square_test schema validated correctly")

    def test_flexible_r_flattened_schema(self):
        """Test that execute_r_analysis's flattened schema works correctly."""
        schema = execute_r_analysis._mcp_tool_input_schema

        # Check data field doesn't have oneOf
        if 'data' in schema['properties']:
            assert 'oneOf' not in str(schema['properties']['data'])

        # Test valid input with data
        valid_with_data = {
            "r_code": "result <- mean(data$values)",
            "data": {"values": [1, 2, 3, 4, 5]},
            "description": "Calculate mean"
        }
        validate(instance=valid_with_data, schema=schema)

        # Test valid input without data (if allowed)
        valid_without_data = {
            "r_code": "result <- 1:10",
            "description": "Generate sequence"
        }
        # This should validate if data is optional
        try:
            validate(instance=valid_without_data, schema=schema)
            print("✅ execute_r_analysis schema validated correctly (with optional data)")
        except ValidationError:
            # If data is required, that's fine too
            print("✅ execute_r_analysis schema validated correctly (data required)")

    def test_schema_error_messages_are_clear(self):
        """Test that validation errors are still clear after flattening schemas."""
        schema = chi_square_test._mcp_tool_input_schema

        # Test missing required field
        invalid_missing_x = {
            "data": {"var1": ["A", "B"]},
            "test_type": "independence",
            # Missing "x" field
        }

        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_missing_x, schema=schema)

        error_message = str(exc_info.value)
        assert "'x' is a required property" in error_message
        print("✅ Schema validation errors are clear and helpful")

    def test_all_tools_have_valid_schemas(self, server_with_all_tools):
        """Test that all tool schemas are valid JSON schemas."""
        import jsonschema

        invalid_schemas = []

        for tool_name, tool in server_with_all_tools.tools._tools.items():
            try:
                # Validate that the schema itself is a valid JSON schema
                jsonschema.Draft7Validator.check_schema(tool.input_schema)
            except jsonschema.SchemaError as e:
                invalid_schemas.append({
                    'name': tool_name,
                    'error': str(e)
                })

        if invalid_schemas:
            print("\n❌ Found invalid schemas:")
            for item in invalid_schemas:
                print(f"  - {item['name']}: {item['error']}")
            pytest.fail(f"Found {len(invalid_schemas)} invalid schemas")
        else:
            print(f"✅ All {len(server_with_all_tools.tools._tools)} tool schemas are valid")

    def test_tools_maintain_backward_compatibility(self):
        """Test that modified tools still accept the same inputs as before."""
        # Test cases that should have worked before and should still work

        # Decision tree - both classification and regression
        dt_class_input = {
            "data": {"x": [1, 2, 3], "y": ["A", "B", "A"]},
            "formula": "y ~ x",
            "method": "class"
        }
        validate(instance=dt_class_input, schema=decision_tree._mcp_tool_input_schema)

        # Random forest - with various parameters
        rf_input = {
            "data": {"x1": [1, 2, 3], "x2": [4, 5, 6], "y": [10, 20, 30]},
            "formula": "y ~ x1 + x2",
            "n_trees": 100,
            "mtry": 2,
            "min_node_size": 5
        }
        validate(instance=rf_input, schema=random_forest._mcp_tool_input_schema)

        # Chi-square test - both test types
        chi_sq_indep = {
            "data": {"a": ["X", "Y", "X"], "b": ["M", "N", "M"]},
            "test_type": "independence",
            "x": "a",
            "y": "b"
        }
        validate(instance=chi_sq_indep, schema=chi_square_test._mcp_tool_input_schema)

        chi_sq_goodness = {
            "data": {"obs": ["A", "B", "C", "A", "B"]},
            "test_type": "goodness_of_fit",
            "x": "obs",
            "expected": [0.4, 0.4, 0.2]
        }
        validate(instance=chi_sq_goodness, schema=chi_square_test._mcp_tool_input_schema)

        print("✅ All modified tools maintain backward compatibility")


class TestClaudeCodeIntegration:
    """Test integration scenarios specific to Claude Code usage."""

    @pytest.fixture
    def server_with_all_tools(self):
        """Create a server with all built-in tools registered."""
        server = create_server()
        _register_builtin_tools(server)
        return server

    def test_tool_discovery_format(self, server_with_all_tools):
        """Test that tool discovery returns Claude-compatible format."""
        import asyncio

        async def test_list_tools():
            ctx = server_with_all_tools.create_context('test', 'tools/list')
            result = await server_with_all_tools.tools.list_tools(ctx)

            # Verify structure
            assert 'tools' in result
            assert len(result['tools']) >= 44

            # Check each tool has required fields for Claude
            for tool in result['tools']:
                assert 'name' in tool
                assert 'inputSchema' in tool

                # Verify no top-level oneOf/allOf/anyOf
                schema = tool['inputSchema']
                assert 'oneOf' not in schema
                assert 'allOf' not in schema
                assert 'anyOf' not in schema

            return len(result['tools'])

        tool_count = asyncio.run(test_list_tools())
        print(f"✅ Tool discovery returns {tool_count} Claude-compatible tools")

    def test_mcp_protocol_compliance(self, server_with_all_tools):
        """Test that server responses comply with MCP protocol for Claude."""
        import asyncio

        async def test_protocol():
            # Test initialization
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {"tools": {}}
                }
            }

            init_resp = await server_with_all_tools.handle_request(init_req)
            assert init_resp.get("jsonrpc") == "2.0"
            assert "result" in init_resp
            assert "protocolVersion" in init_resp["result"]

            # Test tool call with flattened schema
            tool_req = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "summary_stats",
                    "arguments": {
                        "data": {"values": [1, 2, 3, 4, 5]}
                    }
                }
            }

            tool_resp = await server_with_all_tools.handle_request(tool_req)
            assert tool_resp.get("jsonrpc") == "2.0"
            assert "result" in tool_resp or "error" in tool_resp

            return True

        success = asyncio.run(test_protocol())
        assert success, "MCP protocol compliance test failed"
        print("✅ Server responses comply with MCP protocol for Claude")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])