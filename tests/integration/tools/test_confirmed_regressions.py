"""Regression tests for failures found by the end-to-end package audit."""

from __future__ import annotations

import asyncio
from shutil import which

import pytest
from rmcp.cli import _register_builtin_tools
from rmcp.core.context import Context
from rmcp.core.server import create_server

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for these tests"
)


@pytest.fixture(scope="module")
def server():
    """Create a server containing every built-in tool."""
    instance = create_server()
    _register_builtin_tools(instance)
    return instance


def call_tool(server, name: str, arguments: dict) -> dict:
    """Call a registered tool through the same registry used by MCP requests."""
    context = Context.create("audit-regression", "tools/call", server.lifespan_state)
    return asyncio.run(server.tools.call_tool(context, name, arguments))


def assert_success(result: dict) -> dict:
    """Return structured content after asserting that the MCP call succeeded."""
    assert not result.get("isError"), result["content"][0]["text"]
    return result["structuredContent"]


def test_parenthesized_formula_callee_cannot_execute(server, tmp_path):
    marker = tmp_path / "formula-executed"
    command = f"touch {marker}"

    result = call_tool(
        server,
        "linear_model",
        {
            "data": {"y": [1, 2, 3], "cmd": [command, command, command]},
            "formula": "y ~ (system)(cmd)",
        },
    )

    assert result.get("isError") is True
    assert "Unsafe or unsupported R formula syntax" in result["content"][0]["text"]
    assert not marker.exists()


def test_outlier_detection_returns_empty_arrays_when_no_outliers(server):
    result = call_tool(
        server,
        "outlier_detection",
        {"data": {"value": [1, 2, 3, 4, 5]}, "variable": "value"},
    )

    payload = assert_success(result)
    assert payload["outlier_indices"] == []
    assert payload["outlier_values"] == []
    assert payload["n_outliers"] == 0


def test_time_series_plot_accepts_its_declared_data_shape(server):
    result = call_tool(
        server,
        "time_series_plot",
        {
            "data": {
                "values": [10, 12, 11, 15],
                "dates": ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"],
            },
            "show_trend": False,
            "return_image": False,
        },
    )

    payload = assert_success(result)
    assert payload["plot_type"] == "time_series_plot"
    assert payload["statistics"]["n_obs"] == 4
    assert payload["has_dates"] is True
    assert payload["time_axis"] == {
        "type": "date",
        "start": "2026-01-01",
        "end": "2026-04-01",
        "span_days": 90,
    }
    assert payload["show_trend"] is False


def test_time_series_plot_rejects_mismatched_dates(server):
    result = call_tool(
        server,
        "time_series_plot",
        {
            "data": {
                "values": [10, 12, 11, 15],
                "dates": ["2026-01-01", "2026-02-01"],
            },
            "return_image": False,
        },
    )

    assert result.get("isError") is True
    assert "must have equal lengths" in result["content"][0]["text"]


@pytest.mark.parametrize(
    ("operator", "operand", "values", "expected"),
    [
        ("%in%", [1, 3], [1, 2, 3], [1, 3]),
        ("!%in%", [1, 3], [1, 2, 3], [2]),
        ("%in%", [None], [1, None, 2, 3], [None]),
        ("!%in%", [None], [1, None, 2, 3], [1, 2, 3]),
    ],
)
def test_filter_data_membership_arrays_are_values_not_nested_lists(
    server, operator, operand, values, expected
):
    result = call_tool(
        server,
        "filter_data",
        {
            "data": {"x": values},
            "conditions": [{"variable": "x", "operator": operator, "value": operand}],
        },
    )

    payload = assert_success(result)
    assert payload["data"]["x"] == expected


def test_filter_data_combines_null_scalar_and_membership_conditions(server):
    result = call_tool(
        server,
        "filter_data",
        {
            "data": {"id": [1, 2, 3], "x": [1, None, 3], "g": ["a", "c", "b"]},
            "conditions": [
                {"variable": "x", "operator": "!=", "value": None},
                {"variable": "g", "operator": "%in%", "value": ["a", "b"]},
            ],
        },
    )

    payload = assert_success(result)
    assert payload["data"]["id"] == [1, 3]


def test_correlation_heatmap_defaults_to_numeric_columns(server):
    result = call_tool(
        server,
        "correlation_heatmap",
        {
            "data": {
                "x": [1, 2, 3, 4],
                "y": [8, 6, 4, 2],
                "group": ["a", "a", "b", "b"],
            },
            "return_image": False,
        },
    )

    payload = assert_success(result)
    assert payload["variables"] == ["x", "y"]
    assert payload["n_variables"] == 2


def test_correlation_heatmap_preserves_undefined_coefficients(server):
    result = call_tool(
        server,
        "correlation_heatmap",
        {
            "data": {"x": [1, 1, 1], "y": [2, 2, 2]},
            "return_image": False,
        },
    )

    payload = assert_success(result)
    assert payload["correlation_matrix"] == {
        "x": [1, None],
        "y": [None, 1],
    }


def test_regression_plot_matches_declared_output_schema(server):
    result = call_tool(
        server,
        "regression_plot",
        {
            "data": {"x": [1, 2, 3, 4, 5], "y": [3, 5, 7, 9, 11]},
            "formula": "y ~ x",
            "residual_plots": False,
            "return_image": False,
        },
    )

    payload = assert_success(result)
    assert payload["plot_type"] == "regression_plot"
    assert payload["r_squared"] == pytest.approx(1)
    assert payload["adj_r_squared"] == pytest.approx(1)
    assert payload["residual_se"] == pytest.approx(0, abs=1e-12)
    assert payload["residual_plots"] is False
    assert payload["n_obs"] == 5


def test_regression_plot_aligns_rows_after_missing_values_are_omitted(server):
    result = call_tool(
        server,
        "regression_plot",
        {
            "data": {"x": [1, 2, 3, 4], "y": [3, None, 7, 9]},
            "formula": "y ~ x",
            "residual_plots": False,
            "return_image": False,
        },
    )

    payload = assert_success(result)
    assert payload["n_obs"] == 3
    assert payload["r_squared"] == pytest.approx(1)


def test_validate_data_honors_analysis_type_and_strict_mode(server):
    result = call_tool(
        server,
        "validate_data",
        {
            "data": {"value": [1, 1, 2], "label": ["a", "a", "b"]},
            "analysis_type": "correlation",
            "strict": True,
        },
    )

    payload = assert_success(result)
    assert payload["is_valid"] is False
    assert "Correlation requires at least 2 numeric variables" in payload["errors"]
    assert payload["data_quality"]["data_issues"]["duplicate_rows"] == 1
