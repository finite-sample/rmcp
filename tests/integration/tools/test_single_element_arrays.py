#!/usr/bin/env python3
"""Array-typed outputs must stay arrays when R produces exactly one element.

``toJSON(auto_unbox = TRUE)`` collapses a length-1 vector to a bare scalar, so
a tool whose schema requires an array fails output validation on exactly the
inputs users hit most: one variable, one outlier, one forecast period. R
scripts guard this with ``I()``.

Zero elements and two-plus elements already worked; the length-1 case is the
one that broke, so that is what these exercise.
"""

import asyncio
from shutil import which

import pytest

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for these tests"
)

from rmcp.cli import _register_builtin_tools
from rmcp.core.context import Context, LifespanState
from rmcp.core.server import create_server

# One variable, and one outlier in it -- the length-1 case for every tool below.
ONE_VAR = {"x": [1.0, 2.0, 3.0, 4.0, 100.0]}


@pytest.fixture(scope="module")
def server():
    srv = create_server()
    _register_builtin_tools(srv)
    return srv


def _call(server, name, arguments, tmp_path=None):
    lifespan = LifespanState()
    if tmp_path is not None:
        lifespan.allowed_paths = [tmp_path]
    context = Context.create("test", "test", lifespan)
    return asyncio.run(server.tools.call_tool(context, name, arguments))


def _assert_ok(result, tool):
    assert not result.get("isError"), (
        f"{tool} failed on single-element output: {result['content'][0]['text'][:200]}"
    )


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("outlier_detection", {"data": ONE_VAR, "variable": "x"}),
        ("standardize", {"data": ONE_VAR, "variables": ["x"]}),
        (
            "kmeans_clustering",
            {
                "data": {"x": [1.0, 2, 3, 9, 10], "y": [1.0, 2, 3, 9, 10]},
                "variables": ["x"],
                "k": 2,
            },
        ),
        ("validate_data", {"data": {"x": [1.0, 2, 3]}}),
        ("summary_stats", {"data": ONE_VAR, "variables": ["x"]}),
        ("winsorize", {"data": ONE_VAR, "variables": ["x"]}),
        ("difference", {"data": ONE_VAR, "variables": ["x"]}),
        ("lag_lead", {"data": ONE_VAR, "variables": ["x"], "lags": [1]}),
    ],
)
def test_single_variable_output_validates(server, tool, arguments):
    _assert_ok(_call(server, tool, arguments), tool)


def test_write_json_single_variable(server, tmp_path):
    result = _call(
        server,
        "write_json",
        {"data": ONE_VAR, "file_path": str(tmp_path / "out.json")},
        tmp_path=tmp_path,
    )
    _assert_ok(result, "write_json")


def test_arima_single_forecast_period(server):
    """forecast_periods=1 makes every forecast array length 1."""
    values = []
    prev = 10.0
    for i in range(60):
        prev = 0.7 * prev + 3 + (i % 5)
        values.append(round(prev, 3))

    result = _call(
        server, "arima_model", {"data": {"values": values}, "forecast_periods": 1}
    )
    _assert_ok(result, "arima_model")


def test_outlier_values_is_a_list_not_a_scalar(server):
    """Assert the JSON type reaching the client, not just that the call passed.

    Schema validation is what catches this today, but asserting the type
    directly keeps the test meaningful if the schema is ever relaxed.
    """
    result = _call(server, "outlier_detection", {"data": ONE_VAR, "variable": "x"})
    _assert_ok(result, "outlier_detection")

    payload = result["structuredContent"]
    assert isinstance(payload["outlier_values"], list), payload["outlier_values"]
    assert isinstance(payload["outlier_indices"], list), payload["outlier_indices"]
    assert len(payload["outlier_values"]) == 1
