"""Integration tests that exercise the MCP protocol interface."""

from __future__ import annotations

from collections.abc import Callable
from shutil import which
from typing import Any

import pytest
from rmcp.tools.regression import (
    correlation_analysis,
    linear_model,
    logistic_regression,
)

from tests.utils import extract_json_content

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for MCP integration tests"
)


@pytest.fixture
def mcp_server(server_factory):
    """Return a server preloaded with the regression tools used in the tests."""
    return server_factory(linear_model, correlation_analysis, logistic_regression)


def _tool_call_request(
    tool_name: str, arguments: dict[str, Any], *, request_id: int
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def _parse_result(response: dict[str, Any]) -> dict[str, Any]:
    assert "result" in response, f"Response missing result payload: {response!r}"
    result = response["result"]
    assert not result.get("isError", False), f"Tool reported error: {result!r}"
    return extract_json_content(response)


@pytest.mark.asyncio
async def test_tool_discovery(mcp_server, context_factory):
    """Claude Desktop should be able to discover all registered tools."""
    context = context_factory(mcp_server, request_id="discover", method="tools/list")
    response = await mcp_server.tools.list_tools(context)
    tool_names = {tool["name"] for tool in response["tools"]}
    assert tool_names == {
        "linear_model",
        "correlation_analysis",
        "logistic_regression",
    }


def _assert_business_analysis(result: dict[str, Any]) -> None:
    marketing_coef = result["coefficients"]["marketing"]
    r_squared = result["r_squared"]
    p_value = result["p_values"]["marketing"]
    assert marketing_coef > 0, "Marketing spend should increase sales"
    assert r_squared > 0.8, "Model should explain most of the variance"
    assert p_value < 0.05, "Marketing effect should be statistically significant"


def _assert_economist_analysis(result: dict[str, Any]) -> None:
    correlation = result["correlation_matrix"]["gdp_growth"]["unemployment"]
    assert correlation < 0, (
        "GDP growth and unemployment should be negatively correlated"
    )
    assert abs(correlation) > 0.5, "Correlation should be substantial"


def _assert_data_scientist_analysis(result: dict[str, Any]) -> None:
    accuracy = result.get("accuracy", 0)
    tenure_coef = result["coefficients"]["tenure_months"]
    charges_coef = result["coefficients"]["monthly_charges"]
    assert accuracy > 0.6, "Model should be reasonably accurate"
    assert tenure_coef < 0, "Longer tenure should reduce churn likelihood"
    assert charges_coef > 0, "Higher charges should increase churn likelihood"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "validator"),
    [
        (
            "linear_model",
            {
                "data": {
                    "sales": [120, 135, 128, 142, 156, 148, 160, 175],
                    "marketing": [10, 12, 11, 14, 16, 15, 18, 20],
                },
                "formula": "sales ~ marketing",
            },
            _assert_business_analysis,
        ),
        (
            "correlation_analysis",
            {
                "data": {
                    "gdp_growth": [2.1, 2.3, 1.8, 2.5, 2.7, 2.2],
                    "unemployment": [5.2, 5.0, 5.5, 4.8, 4.5, 4.9],
                },
                "variables": ["gdp_growth", "unemployment"],
                "method": "pearson",
            },
            _assert_economist_analysis,
        ),
        (
            "logistic_regression",
            {
                "data": {
                    "churn": [0, 1, 0, 1, 0, 0, 1, 1, 0, 1],
                    "tenure_months": [24, 6, 36, 3, 48, 18, 9, 2, 60, 4],
                    "monthly_charges": [70, 85, 65, 90, 60, 75, 95, 100, 55, 88],
                },
                "formula": "churn ~ tenure_months + monthly_charges",
                "family": "binomial",
                "link": "logit",
            },
            _assert_data_scientist_analysis,
        ),
    ],
)
async def test_mcp_tool_calls(
    mcp_server,
    tool_name: str,
    arguments: dict[str, Any],
    validator: Callable[[dict[str, Any]], None],
):
    """Exercise representative MCP tool calls and validate the returned results."""
    response = await mcp_server.handle_request(
        _tool_call_request(tool_name, arguments, request_id=1)
    )
    result = _parse_result(response)
    validator(result)


@pytest.mark.asyncio
async def test_invalid_tool_request_returns_error(mcp_server):
    """Requests for unknown tools should yield a JSON-RPC error response."""
    response = await mcp_server.handle_request(
        _tool_call_request("nonexistent_tool", {"data": [1, 2, 3]}, request_id=99)
    )
    assert "error" in response
    assert response["error"]["message"] == "Unknown tool: nonexistent_tool"
