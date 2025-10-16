"""Unit tests for common error scenarios exposed through the MCP server.

These tests focus on schema validation and pure Python logic that doesn't require R.
Tests that require R execution have been moved to integration tests.
"""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.formula_builder import build_formula
from rmcp.tools.helpers import suggest_fix
from rmcp.tools.regression import linear_model
from tests.utils import extract_json_content, extract_text_summary


async def _call_tool(
    tool: Callable[..., Awaitable[dict[str, Any]]],
    arguments: dict[str, Any],
    *extra_tools: Callable[..., Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    """Invoke ``tool`` through the MCP server and return the JSON-RPC response."""
    server = create_server()
    register_tool_functions(server.tools, tool, *extra_tools)
    tool_name = getattr(tool, "_mcp_tool_name")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    return await server.handle_request(request)


def _extract_text_content(response: dict[str, Any]) -> str:
    """Return the concatenated human-readable text payload for a tool response."""
    text = extract_text_summary(response)
    assert text, "tool response must include human-readable text"
    return text


@pytest.mark.asyncio
async def test_missing_required_parameters_returns_schema_error():
    response = await _call_tool(linear_model, {"formula": "y ~ x"})
    assert response["result"]["isError"] is True
    text = _extract_text_content(response)
    assert "'data' is a required property" in text


@pytest.mark.asyncio
async def test_invalid_data_types_are_rejected():
    response = await _call_tool(
        linear_model,
        {"data": "this_should_be_a_dict", "formula": "y ~ x"},
    )
    assert response["result"]["isError"] is True
    text = _extract_text_content(response)
    assert "is not of type 'object'" in text


# Tests for R execution errors have been moved to tests/integration/test_r_error_handling.py
# These tests now use real R execution instead of mocks


@pytest.mark.asyncio
async def test_invalid_formulas_fail_schema_validation():
    response = await _call_tool(
        linear_model,
        {
            "data": {"x": [1, 2, 3, 4], "y": [2, 4, 6, 8]},
            "formula": "invalid ~ ~ syntax error",
        },
    )
    assert response["result"]["isError"] is True
    text = _extract_text_content(response)
    assert "does not match" in text
    assert "formula" in text


# File operation error tests moved to tests/integration/test_r_error_handling.py


@pytest.mark.asyncio
async def test_suggest_fix_returns_structured_analysis():
    response = await _call_tool(
        suggest_fix,
        {"error_message": "there is no package called 'nonexistent'"},
    )
    assert "isError" not in response["result"]
    payload = extract_json_content(response)
    assert payload["error_type"] == "missing_package"
    assert any("install" in suggestion.lower() for suggestion in payload["suggestions"])


# Data validation tests moved to tests/integration/test_r_error_handling.py


@pytest.mark.asyncio
async def test_ambiguous_formula_description_still_produces_formula():
    """Test pure Python pattern matching - no R validation since no data provided."""
    response = await _call_tool(
        build_formula,
        {"description": "something something random words"},
    )
    assert "isError" not in response["result"]
    payload = extract_json_content(response)
    assert payload["formula"].startswith("something ~")
    assert payload["matched_pattern"] == "manual extraction"
