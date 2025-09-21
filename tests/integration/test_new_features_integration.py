"""Integration tests for the feature set introduced in v0.3.6."""

from __future__ import annotations

import ast
import json
from shutil import which
from typing import Any, Dict

import pytest

from rmcp.tools.fileops import read_excel, read_json
from rmcp.tools.formula_builder import build_formula, validate_formula
from rmcp.tools.helpers import load_example, suggest_fix, validate_data
from rmcp.tools.regression import correlation_analysis, linear_model

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for integration tests"
)


@pytest.fixture
def integration_server(server_factory):
    """Return a server with the toolchain required for the new feature flows."""

    return server_factory(
        build_formula,
        validate_formula,
        suggest_fix,
        validate_data,
        load_example,
        read_json,
        read_excel,
        linear_model,
        correlation_analysis,
    )


def _tool_call_request(tool_name: str, arguments: Dict[str, Any], *, request_id: int) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def _parse_result(response: Dict[str, Any]) -> Dict[str, Any]:
    assert "result" in response, f"Response missing result payload: {response!r}"
    result = response["result"]
    assert not result.get("isError", False), f"Tool reported error: {result!r}"
    content = result.get("content")
    assert content, f"No content returned from tool: {result!r}"

    payload = content[0]["text"]
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return ast.literal_eval(payload)


async def _call_tool(server: Any, name: str, arguments: Dict[str, Any], *, request_id: int) -> Dict[str, Any]:
    response = await server.handle_request(_tool_call_request(name, arguments, request_id=request_id))
    return _parse_result(response)


@pytest.mark.asyncio
async def test_formula_to_analysis_workflow(integration_server):
    """Validate the natural-language to analysis workflow end-to-end."""

    formula_result = await _call_tool(
        integration_server,
        "build_formula",
        {"description": "predict satisfaction from purchase frequency"},
        request_id=1,
    )
    formula = formula_result["formula"]
    assert formula

    dataset_result = await _call_tool(
        integration_server,
        "load_example",
        {"dataset_name": "survey", "size": "small"},
        request_id=2,
    )
    dataset = dataset_result["data"]
    assert dataset
    assert dataset_result["metadata"]["rows"] > 0

    validation_result = await _call_tool(
        integration_server,
        "validate_formula",
        {"formula": "satisfaction ~ purchase_frequency", "data": dataset},
        request_id=3,
    )
    assert validation_result["is_valid"]

    analysis_result = await _call_tool(
        integration_server,
        "correlation_analysis",
        {"data": dataset, "method": "pearson"},
        request_id=4,
    )
    assert analysis_result["correlation_matrix"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        {
            "error": "there is no package called 'forecast'",
            "tool": "arima_model",
            "expected_type": "missing_package",
        },
        {
            "error": "object 'sales' not found",
            "tool": "linear_model",
            "expected_type": "missing_variable",
        },
        {
            "error": "invalid formula syntax",
            "tool": "correlation_analysis",
            "expected_type": "formula_syntax",
        },
    ],
)
async def test_error_recovery_workflow(integration_server, scenario: Dict[str, Any]):
    """Ensure error diagnosis suggestions are returned for common failure modes."""

    result = await _call_tool(
        integration_server,
        "suggest_fix",
        {
            "error_message": scenario["error"],
            "tool_name": scenario["tool"],
        },
        request_id=10,
    )

    assert result["error_type"] == scenario["expected_type"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("dataset_name", "analysis_type"),
    [
        ("sales", "regression"),
        ("customers", "classification"),
        ("economics", "correlation"),
    ],
)
async def test_data_validation_integration(
    integration_server, dataset_name: str, analysis_type: str
):
    """Datasets loaded via helpers should pass validation for the requested analysis types."""

    dataset_result = await _call_tool(
        integration_server,
        "load_example",
        {"dataset_name": dataset_name, "size": "small"},
        request_id=20,
    )
    dataset = dataset_result["data"]
    assert dataset

    validation_result = await _call_tool(
        integration_server,
        "validate_data",
        {"data": dataset, "analysis_type": analysis_type},
        request_id=21,
    )
    assert "is_valid" in validation_result
