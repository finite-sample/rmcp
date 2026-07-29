#!/usr/bin/env python3
"""Degenerate-but-ordinary inputs, driven over the real MCP protocol.

Every other test for these bugs calls ``ToolsRegistry.call_tool`` directly,
which skips the transport, the SDK adapter, and serialisation to the client.
These bugs are *about what reaches the client*, so they are proven here
instead: ``run_mcp_stdio_workflow`` spawns ``rmcp start`` as a subprocess and
drives it with the official MCP client over stdio -- the same protocol and
client library Claude Desktop uses.

The inputs are the ones that used to fail: one variable, one row, one forecast
period, a 2x2 contingency table. A tool that emits a scalar where its schema
declares an array fails validation inside the server, and the client sees
``isError``.
"""

import sys
from shutil import which

import pytest

pytestmark = [
    pytest.mark.skipif(which("R") is None, reason="R binary is required"),
    pytest.mark.skipif(
        which("rmcp") is None and not sys.executable,
        reason="rmcp entry point is required",
    ),
]

from tests.utils import run_mcp_stdio_workflow

ONE_VAR = {"x": [1.0, 2.0, 3.0, 4.0, 100.0]}
ONE_ROW = {"x": [5.0], "g": ["a"]}
TWO_BY_TWO = {
    "a": ["p", "q", "p", "q", "p", "q", "p", "q"],
    "b": ["r", "s", "s", "r", "r", "s", "s", "r"],
}


def _trending_series() -> list[float]:
    values, prev = [], 10.0
    for i in range(60):
        prev = 0.7 * prev + 3 + (i % 5)
        values.append(round(prev, 3))
    return values


#: (label, tool, arguments) -- each previously produced an isError result.
DEGENERATE_CALLS = [
    ("one variable", "outlier_detection", {"data": ONE_VAR, "variable": "x"}),
    ("one variable", "standardize", {"data": ONE_VAR, "variables": ["x"]}),
    ("one variable", "summary_stats", {"data": ONE_VAR, "variables": ["x"]}),
    ("one suggestion", "validate_data", {"data": {"x": [1.0, 2.0, 3.0]}}),
    ("one row", "winsorize", {"data": ONE_ROW, "variables": ["x"]}),
    ("one row", "difference", {"data": ONE_ROW, "variables": ["x"]}),
    ("one row", "lag_lead", {"data": ONE_ROW, "variables": ["x"], "lags": [1]}),
    ("one row", "summary_stats", {"data": ONE_ROW, "variables": ["x"]}),
    ("one row", "standardize", {"data": ONE_ROW, "variables": ["x"]}),
    (
        "2x2 table",
        "chi_square_test",
        {"data": TWO_BY_TWO, "x": "a", "y": "b", "test_type": "independence"},
    ),
    (
        "one forecast period",
        "arima_model",
        {"data": {"values": _trending_series()}, "forecast_periods": 1},
    ),
    (
        "two variables",
        "correlation_heatmap",
        {
            "data": {"x": [1.0, 2, 3, 4, 5, 6], "y": [2.0, 4, 5, 4, 6, 7]},
            "variables": ["x", "y"],
        },
    ),
]


@pytest.fixture(scope="module")
def mcp_session():
    """One stdio server run covering every call, since startup is the slow part."""
    init, tool_names, results = run_mcp_stdio_workflow(
        command=sys.executable,
        args=["-m", "rmcp.cli", "start"],
        tool_calls=[(tool, args) for _, tool, args in DEGENERATE_CALLS],
        timeout=300.0,
    )
    return init, tool_names, results


def test_server_initializes_over_stdio(mcp_session):
    init, tool_names, _ = mcp_session
    assert init["protocolVersion"]
    assert init["serverInfo"]["name"]
    assert len(tool_names) > 40


def test_no_degenerate_input_produces_an_error(mcp_session):
    """The headline: none of these should come back as isError."""
    _, _, results = mcp_session
    failures = []
    for (label, tool, _), result in zip(DEGENERATE_CALLS, results, strict=True):
        if result.get("isError"):
            text = (result.get("content") or [{}])[0].get("text", "")
            failures.append(f"{tool} ({label}): {text[:160]}")

    assert not failures, "tools failed on ordinary input:\n" + "\n".join(failures)


def test_arrays_reach_the_client_as_arrays(mcp_session):
    """Absence of error is not enough -- check the JSON types the client sees."""
    _, _, results = mcp_session
    by_tool = {
        tool: result
        for (_, tool, _), result in zip(DEGENERATE_CALLS, results, strict=True)
        if not result.get("isError")
    }

    outliers = by_tool.get("outlier_detection", {}).get("structuredContent")
    assert outliers is not None, "outlier_detection returned no structuredContent"
    assert isinstance(outliers["outlier_values"], list)
    assert isinstance(outliers["outlier_indices"], list)
    assert len(outliers["outlier_values"]) == 1, "the single-element case"

    # The nested payload is the case the first round of fixes missed.
    winsorized = by_tool.get("winsorize", {}).get("structuredContent")
    assert winsorized is not None
    assert isinstance(winsorized["data"]["x"], list)
    assert len(winsorized["data"]["x"]) == 1


def test_chi_square_contingency_table_serializes(mcp_session):
    """Independence tests died on `No method asJSON S3 class: table`."""
    _, _, results = mcp_session
    result = dict(zip([t for _, t, _ in DEGENERATE_CALLS], results, strict=True))[
        "chi_square_test"
    ]
    assert not result.get("isError"), result.get("content")
    payload = result["structuredContent"]
    assert payload["contingency_table"], "contingency table missing"
    assert payload["expected_frequencies"], "expected frequencies missing"
