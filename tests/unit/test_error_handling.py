"""Unit tests for common error scenarios exposed through the MCP server."""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.tools.fileops import read_csv
from rmcp.tools.formula_builder import build_formula
from rmcp.tools.helpers import suggest_fix, validate_data
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


@pytest.mark.asyncio
async def test_empty_data_produces_tool_execution_error(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_execute_r_script_async(script: str, params: dict[str, Any]):
        raise RuntimeError("dataset is empty")

    monkeypatch.setattr(
        "rmcp.tools.regression.execute_r_script_async",
        fake_execute_r_script_async,
    )

    response = await _call_tool(linear_model, {"data": {}, "formula": "y ~ x"})

    assert response["result"]["isError"] is True
    assert "Tool execution error: dataset is empty" in _extract_text_content(response)


@pytest.mark.asyncio
async def test_malformed_data_surfaces_execution_error(monkeypatch: pytest.MonkeyPatch):
    async def fake_execute_r_script_async(script: str, params: dict[str, Any]):
        raise ValueError("non-numeric value encountered in column 'x'")

    monkeypatch.setattr(
        "rmcp.tools.regression.execute_r_script_async",
        fake_execute_r_script_async,
    )

    response = await _call_tool(
        linear_model,
        {
            "data": {"x": [1, 2, "not_a_number", 4], "y": [1, 2, 3, 4]},
            "formula": "y ~ x",
        },
    )

    assert response["result"]["isError"] is True
    assert "non-numeric value encountered" in _extract_text_content(response)


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


@pytest.mark.asyncio
async def test_nonexistent_file_errors_are_reported(monkeypatch: pytest.MonkeyPatch):
    async def fake_execute_r_script_async(script: str, params: dict[str, Any]):
        raise FileNotFoundError(f"File not found: {params['file_path']}")

    monkeypatch.setattr(
        "rmcp.tools.fileops.execute_r_script_async",
        fake_execute_r_script_async,
    )

    response = await _call_tool(read_csv, {"file_path": "/missing/data.csv"})

    assert response["result"]["isError"] is True
    text = _extract_text_content(response)
    assert "Tool execution error" in text
    assert "/missing/data.csv" in text


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


@pytest.mark.asyncio
async def test_data_validation_edge_cases_surface_warnings(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_execute_r_script_async(script: str, params: dict[str, Any]):
        return {
            "is_valid": False,
            "warnings": ["High missing values in: x"],
            "errors": ["Dataset is empty (no rows)"],
            "suggestions": ["Provide at least one observation"],
            "data_quality": {
                "dimensions": {"rows": 3, "columns": 2},
                "variable_types": {
                    "numeric": 1,
                    "character": 0,
                    "factor": 0,
                    "logical": 0,
                },
                "missing_values": {
                    "total_missing_cells": 3,
                    "variables_with_missing": 1,
                    "max_missing_percentage": 100.0,
                },
                "data_issues": {
                    "constant_variables": 0,
                    "high_outlier_variables": 0,
                    "duplicate_rows": 0,
                },
            },
        }

    monkeypatch.setattr(
        "rmcp.tools.helpers.execute_r_script_async",
        fake_execute_r_script_async,
    )

    response = await _call_tool(
        validate_data,
        {"data": {"x": [None, None, None], "y": [float("inf"), -float("inf"), 3]}},
    )

    assert "isError" not in response["result"]
    payload = extract_json_content(response)
    assert payload["is_valid"] is False
    assert payload["errors"]
    assert payload["warnings"]


@pytest.mark.asyncio
async def test_ambiguous_formula_description_still_produces_formula():
    response = await _call_tool(
        build_formula,
        {"description": "something something random words"},
    )

    assert "isError" not in response["result"]
    payload = extract_json_content(response)
    assert payload["formula"].startswith("something ~")
    assert payload["matched_pattern"] == "manual extraction"
