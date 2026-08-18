"""Protocol-level RMCP evaluations with semantic and adversarial oracles."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from os import environ
from pathlib import Path
from shutil import which
from typing import Any

import pytest
from rmcp.cli import _register_builtin_tools
from rmcp.core.context import Context
from rmcp.core.server import create_server
from tests.utils import run_mcp_stdio_workflow

pytestmark = pytest.mark.skipif(
    which("R") is None and not environ.get("RMCP_EVAL_DOCKER_IMAGE"),
    reason="R binary or RMCP_EVAL_DOCKER_IMAGE is required for MCP evaluations",
)

Oracle = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class EvalCase:
    """One versioned MCP behavior contract."""

    case_id: str
    layer: str
    intent: str
    tool: str
    arguments: dict[str, Any]
    oracle: Oracle | None = None
    error_contains: str | None = None
    error_excludes: tuple[str, ...] = ()


def _exact_linear_model(payload: dict[str, Any]) -> None:
    assert payload["coefficients"]["(Intercept)"] == pytest.approx(1)
    assert payload["coefficients"]["x"] == pytest.approx(2)
    assert payload["r_squared"] == pytest.approx(1)


def _standardized(payload: dict[str, Any]) -> None:
    values = payload["data"]["x_z_score"]
    assert sum(values) / len(values) == pytest.approx(0, abs=1e-10)
    assert sum(value**2 for value in values) / (len(values) - 1) == pytest.approx(
        1, abs=5e-5
    )


def _strict_data_audit(payload: dict[str, Any]) -> None:
    assert payload["is_valid"] is False
    assert payload["data_quality"]["data_issues"]["duplicate_rows"] == 1
    assert any("Correlation requires" in error for error in payload["errors"])


def _csv_written(payload: dict[str, Any]) -> None:
    assert payload["success"] is True
    assert payload["rows_written"] == 3
    assert payload["cols_written"] == 2


def _write_approved(payload: dict[str, Any]) -> None:
    assert payload["success"] is True
    assert payload["action"] == "approved"


def _csv_read(payload: dict[str, Any]) -> None:
    assert payload["file_info"]["n_rows"] == 3
    assert payload["file_info"]["column_names"] == ["x", "label"]
    assert payload["data"]["x"] == [1, 2, 3]


def _missing_package_diagnosis(payload: dict[str, Any]) -> None:
    assert payload["error_type"] == "missing_package"
    assert any("install.packages" in item for item in payload["suggestions"])


def _no_outliers(payload: dict[str, Any]) -> None:
    assert payload["n_outliers"] == 0
    assert payload["outlier_values"] == []


def _summary_identity(payload: dict[str, Any]) -> None:
    assert payload["n_obs"] == 4
    assert payload["statistics"]["x"]["mean"] == pytest.approx(2.5)
    assert payload["statistics"]["x"]["min"] == 1
    assert payload["statistics"]["x"]["max"] == 4


def _frequency_identity(payload: dict[str, Any]) -> None:
    table = payload["frequency_tables"]["group"]
    counts = dict(zip(table["values"], table["frequencies"], strict=True))
    assert counts == {"a": 2, "b": 1}


def _second_difference(payload: dict[str, Any]) -> None:
    assert payload["difference_order"] == 2
    assert payload["data"]["x_diff2"] == [None, None, 2, 2, 2]


def _lag_lead_identity(payload: dict[str, Any]) -> None:
    assert payload["data"]["x_lag1"] == [None, 10, 20]
    assert payload["data"]["x_lead1"] == [20, 30, None]


def _literal_filter_value(payload: dict[str, Any]) -> None:
    assert payload["filtered_rows"] == 1
    assert payload["data"]["id"] == [2]


def _membership_filter(payload: dict[str, Any]) -> None:
    assert payload["filtered_rows"] == 2
    assert payload["data"]["x"] == [1, 3]


def _missing_filter(payload: dict[str, Any]) -> None:
    assert payload["filtered_rows"] == 1
    assert payload["data"]["id"] == [2]


def _invalid_formula(payload: dict[str, Any]) -> None:
    assert payload["is_valid"] is False
    assert payload["formula_parsed"] is False
    assert payload["analysis_type"] == "regression"


def _two_cluster_solution(payload: dict[str, Any]) -> None:
    assert payload["k"] == 2
    assert payload["n_obs"] == 6
    assert sorted(payload["cluster_sizes"].values()) == [3, 3]
    assert payload["silhouette_score"] > 0.9


def _arima_forecast(payload: dict[str, Any]) -> None:
    assert payload["model_type"] == "ARIMA"
    assert payload["n_obs"] == 30
    assert len(payload["forecasts"]) == 3
    assert len(payload["forecast_lower"]) == 3
    assert len(payload["forecast_upper"]) == 3


def _random_forest_fit(payload: dict[str, Any]) -> None:
    assert payload["problem_type"] == "regression"
    assert payload["n_obs"] == 20
    assert payload["n_trees"] == 25
    assert payload["mtry"] == 2


def _panel_fit(payload: dict[str, Any]) -> None:
    assert payload["model_type"] == "pooling"
    assert payload["n_obs"] == 12
    assert payload["n_groups"] == 3
    assert payload["time_periods"] == 4


def _one_point_time_series(payload: dict[str, Any]) -> None:
    assert payload["statistics"]["n_obs"] == 1
    assert payload["statistics"]["mean"] == 7
    assert payload["statistics"]["sd"] is None


def _two_point_regression(payload: dict[str, Any]) -> None:
    assert payload["n_obs"] == 2
    assert payload["r_squared"] == pytest.approx(1)
    assert payload["adj_r_squared"] is None
    assert payload["residual_se"] is None


CASES = (
    EvalCase(
        "known-linear-effect",
        "semantic",
        "Recover y = 1 + 2x exactly",
        "linear_model",
        {"data": {"x": [1, 2, 3, 4, 5], "y": [3, 5, 7, 9, 11]}, "formula": "y ~ x"},
        oracle=_exact_linear_model,
    ),
    EvalCase(
        "z-score-identity",
        "semantic",
        "Standardize a numeric column to sample mean zero and variance one",
        "standardize",
        {"data": {"x": [1, 2, 3, 4, 5]}, "variables": ["x"]},
        oracle=_standardized,
    ),
    EvalCase(
        "strict-data-audit",
        "data-quality",
        "Find duplicates and an invalid correlation design",
        "validate_data",
        {
            "data": {"value": [1, 1, 2], "label": ["a", "a", "b"]},
            "analysis_type": "correlation",
            "strict": True,
        },
        oracle=_strict_data_audit,
    ),
    EvalCase(
        "no-outlier-result",
        "semantic",
        "Return an empty outlier set without failing",
        "outlier_detection",
        {"data": {"x": [1, 2, 3, 4, 5]}, "variable": "x"},
        oracle=_no_outliers,
    ),
    EvalCase(
        "descriptive-identities",
        "semantic",
        "Recover exact descriptive statistics for a tiny dataset",
        "summary_stats",
        {"data": {"x": [1, 2, 3, 4]}},
        oracle=_summary_identity,
    ),
    EvalCase(
        "categorical-counts",
        "semantic",
        "Count category frequencies exactly",
        "frequency_table",
        {"data": {"group": ["a", "b", "a"]}, "variables": ["group"]},
        oracle=_frequency_identity,
    ),
    EvalCase(
        "second-difference",
        "semantic",
        "Honor the advertised second-order differencing argument",
        "difference",
        {"data": {"x": [1, 2, 5, 10, 17]}, "variables": ["x"], "order": 2},
        oracle=_second_difference,
    ),
    EvalCase(
        "lag-and-lead",
        "semantic",
        "Create aligned one-period lags and leads",
        "lag_lead",
        {"data": {"x": [10, 20, 30]}, "variables": ["x"], "lags": [1], "leads": [1]},
        oracle=_lag_lead_identity,
    ),
    EvalCase(
        "filter-data-not-code",
        "safety",
        "Treat an R-like filter value as inert data",
        "filter_data",
        {
            "data": {"id": [1, 2], "label": ["ordinary", "system('false')"]},
            "conditions": [
                {"variable": "label", "operator": "==", "value": "system('false')"}
            ],
        },
        oracle=_literal_filter_value,
    ),
    EvalCase(
        "filter-membership-array",
        "semantic",
        "Treat a membership operand as a flat collection of values",
        "filter_data",
        {
            "data": {"x": [1, 2, 3]},
            "conditions": [{"variable": "x", "operator": "%in%", "value": [1, 3]}],
        },
        oracle=_membership_filter,
    ),
    EvalCase(
        "filter-missing-value",
        "semantic",
        "Use null equality to select missing observations",
        "filter_data",
        {
            "data": {"id": [1, 2, 3], "x": [1, None, 3]},
            "conditions": [{"variable": "x", "operator": "==", "value": None}],
        },
        oracle=_missing_filter,
    ),
    EvalCase(
        "invalid-formula-result",
        "recovery",
        "Return a schema-valid diagnosis for malformed formula syntax",
        "validate_formula",
        {"formula": "y plus x", "data": {"x": [1, 2], "y": [2, 4]}},
        oracle=_invalid_formula,
    ),
    EvalCase(
        "separated-kmeans-clusters",
        "semantic",
        "Recover two well-separated groups with the clustering runtime",
        "kmeans_clustering",
        {
            "data": {
                "x": [0, 0.1, -0.1, 10, 10.1, 9.9],
                "y": [0.1, -0.1, 0, 10.1, 9.9, 10],
            },
            "variables": ["x", "y"],
            "k": 2,
        },
        oracle=_two_cluster_solution,
    ),
    EvalCase(
        "arima-forecast-shape",
        "semantic",
        "Fit and forecast a nondegenerate time series with the forecast runtime",
        "arima_model",
        {
            "data": {
                "values": [
                    10,
                    12,
                    11,
                    14,
                    13,
                    15,
                    16,
                    15,
                    18,
                    17,
                    20,
                    19,
                    21,
                    23,
                    22,
                    25,
                    24,
                    27,
                    26,
                    29,
                    31,
                    30,
                    33,
                    32,
                    35,
                    34,
                    37,
                    39,
                    38,
                    41,
                ]
            },
            "order": [1, 1, 1],
            "forecast_periods": 3,
        },
        oracle=_arima_forecast,
    ),
    EvalCase(
        "random-forest-runtime",
        "semantic",
        "Fit a bounded regression forest with the production ML runtime",
        "random_forest",
        {
            "data": {
                "x1": list(range(1, 21)),
                "x2": [value % 3 for value in range(1, 21)],
                "x3": [value % 5 for value in range(1, 21)],
                "y": [2 * value + value % 3 for value in range(1, 21)],
            },
            "formula": "y ~ x1 + x2 + x3",
            "n_trees": 25,
            "mtry": 2,
        },
        oracle=_random_forest_fit,
    ),
    EvalCase(
        "panel-runtime",
        "semantic",
        "Fit a pooling panel model across three balanced groups",
        "panel_regression",
        {
            "data": {
                "id": [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3],
                "time": [1, 2, 3, 4] * 3,
                "x": [1, 2, 3, 4, 2, 3, 4, 5, 3, 4, 5, 6],
                "y": [3, 5, 7, 9, 6, 8, 10, 12, 9, 11, 13, 15],
            },
            "formula": "y ~ x",
            "id_variable": "id",
            "time_variable": "time",
            "model": "pooling",
            "robust": False,
        },
        oracle=_panel_fit,
    ),
    EvalCase(
        "one-point-time-series",
        "boundary",
        "Represent an undefined one-point sample standard deviation as null",
        "time_series_plot",
        {"data": {"values": [7]}, "return_image": False, "show_trend": False},
        oracle=_one_point_time_series,
    ),
    EvalCase(
        "two-point-regression-plot",
        "boundary",
        "Represent residual standard error with zero residual degrees of freedom as null",
        "regression_plot",
        {
            "data": {"x": [1, 2], "y": [3, 5]},
            "formula": "y ~ x",
            "return_image": False,
            "residual_plots": False,
        },
        oracle=_two_point_regression,
    ),
    EvalCase(
        "approve-versioned-data-write",
        "workflow",
        "Grant a session-scoped write to the server workspace",
        "approve_operation",
        {
            "operation_type": "file_operations",
            "specific_operation": "write_csv",
            "directory": ".",
        },
        oracle=_write_approved,
    ),
    EvalCase(
        "write-versioned-data",
        "workflow",
        "Write a small typed dataset to the server workspace",
        "write_csv",
        {"data": {"x": [1, 2, 3], "label": ["a", "b", "c"]}, "file_path": "eval.csv"},
        oracle=_csv_written,
    ),
    EvalCase(
        "read-versioned-data",
        "workflow",
        "Read back the dataset written by the preceding call",
        "read_csv",
        {"file_path": "eval.csv"},
        oracle=_csv_read,
    ),
    EvalCase(
        "diagnose-missing-package",
        "recovery",
        "Turn an R dependency error into a concrete recovery action",
        "suggest_fix",
        {"error_message": "there is no package called 'forecast'"},
        oracle=_missing_package_diagnosis,
    ),
    EvalCase(
        "missing-required-argument",
        "contract",
        "Reject a regression request with no formula",
        "linear_model",
        {"data": {"x": [1, 2], "y": [2, 4]}},
        error_contains="'formula' is a required property",
    ),
    EvalCase(
        "ragged-table",
        "contract",
        "Reject columns with unequal lengths before invoking R",
        "summary_stats",
        {"data": {"x": [1, 2, 3], "y": [1]}},
        error_contains="must have equal lengths",
    ),
    EvalCase(
        "empty-table",
        "contract",
        "Reject an empty dataset before invoking R",
        "summary_stats",
        {"data": {}},
        error_contains="at least one column",
    ),
    EvalCase(
        "formula-code-execution",
        "safety",
        "Reject an R formula that attempts to invoke the operating system",
        "linear_model",
        {
            "data": {"x": [1, 2, 3], "y": [2, 4, 6]},
            "formula": 'y ~ system("true")',
        },
        error_contains="Unsafe or unsupported R formula syntax",
    ),
    EvalCase(
        "unknown-argument",
        "contract",
        "Reject misspelled or stale tool arguments",
        "summary_stats",
        {"data": {"x": [1, 2, 3]}, "varibles": ["x"]},
        error_contains="Additional properties are not allowed",
    ),
    EvalCase(
        "unknown-filter-variable",
        "contract",
        "Reject a filter that names a column absent from the dataset",
        "filter_data",
        {
            "data": {"x": [1, 2, 3]},
            "conditions": [{"variable": "missing", "operator": ">", "value": 1}],
        },
        error_contains="Filter variables not found in data: missing",
    ),
    EvalCase(
        "filter-condition-typo",
        "contract",
        "Reject unknown fields nested inside a filter condition",
        "filter_data",
        {
            "data": {"x": [1, 2, 3]},
            "conditions": [{"variable": "x", "operator": ">", "value": 1, "vale": 2}],
        },
        error_contains="Additional properties are not allowed",
    ),
    EvalCase(
        "filter-array-with-scalar-operator",
        "contract",
        "Reject an array operand for scalar equality before invoking R",
        "filter_data",
        {
            "data": {"x": [1, 2, 3]},
            "conditions": [{"variable": "x", "operator": "==", "value": [1, 3]}],
        },
        error_contains="is not of type 'string', 'number', 'boolean', 'null'",
    ),
    EvalCase(
        "filter-null-ordering",
        "contract",
        "Reject an undefined ordering comparison against null before invoking R",
        "filter_data",
        {
            "data": {"x": [1, None, 3]},
            "conditions": [{"variable": "x", "operator": ">", "value": None}],
        },
        error_contains="is not of type 'string', 'number', 'boolean'",
    ),
    EvalCase(
        "nonnumeric-outlier-variable",
        "contract",
        "Reject a categorical outlier target before invoking R",
        "outlier_detection",
        {"data": {"group": ["a", "b", "c"]}, "variable": "group"},
        error_contains="must contain only numeric values",
    ),
    EvalCase(
        "unknown-variable",
        "execution",
        "Return a tool error when a requested variable does not exist",
        "outlier_detection",
        {"data": {"x": [1, 2, 3]}, "variable": "missing"},
        error_contains="Variable 'missing' was not found in data",
    ),
    EvalCase(
        "underspecified-regression-sanitized",
        "safety",
        "Return a safe R failure without subprocess, path, or environment details",
        "regression_plot",
        {
            "data": {"x": [1], "y": [3]},
            "formula": "y ~ x",
            "return_image": False,
        },
        error_contains="R script execution failed",
        error_excludes=("COMMAND:", "ENVIRONMENT:", "/private/", "/usr/local/"),
    ),
    EvalCase(
        "filesystem-escape",
        "safety",
        "Deny reads outside the configured workspace",
        "read_csv",
        {"file_path": "/etc/passwd"},
        error_contains="Path access denied",
    ),
)


@pytest.fixture(scope="module")
def protocol_run(tmp_path_factory):
    """Run all cases through one real stdio server and official MCP client."""
    working_dir = tmp_path_factory.mktemp("rmcp-evals")
    docker_image = environ.get("RMCP_EVAL_DOCKER_IMAGE")
    if docker_image:
        command = "docker"
        args = ["run", "--rm", "-i", docker_image]
        cwd = None
        env = dict(environ)
    else:
        command = sys.executable
        args = ["-m", "rmcp.cli", "start"]
        cwd = working_dir
        env = None
    init, tool_names, results = run_mcp_stdio_workflow(
        command=command,
        args=args,
        tool_calls=[(case.tool, case.arguments) for case in CASES],
        env=env,
        cwd=cwd,
        timeout=300,
    )
    return (
        working_dir,
        docker_image is not None,
        init,
        tool_names,
        dict(zip((case.case_id for case in CASES), results, strict=True)),
    )


def test_protocol_discovery(protocol_run):
    _, _, init, tool_names, _ = protocol_run
    assert init["protocolVersion"]
    assert init["serverInfo"]["name"] == "RMCP MCP Server"
    assert len(tool_names) == len(set(tool_names))
    assert len(tool_names) >= 50


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.layer}:{case.case_id}")
def test_mcp_behavior_contract(case: EvalCase, protocol_run):
    working_dir, in_container, _, _, results = protocol_run
    result = results[case.case_id]
    text = "\n".join(
        item.get("text", "")
        for item in result.get("content", [])
        if item["type"] == "text"
    )

    if case.error_contains is not None:
        assert result.get("isError") is True, case.intent
        assert case.error_contains in text, text
        for forbidden in case.error_excludes:
            assert forbidden not in text, text
        return

    assert not result.get("isError"), f"{case.intent}: {text}"
    payload = result.get("structuredContent")
    assert isinstance(payload, dict), f"{case.intent}: missing structured content"
    assert case.oracle is not None
    case.oracle(payload)

    if case.case_id == "write-versioned-data" and not in_container:
        assert (Path(working_dir) / "eval.csv").is_file()


@pytest.mark.asyncio
async def test_advertised_tool_contracts_are_unambiguous():
    """Reject exact catalog collisions and permissive top-level schemas."""
    server = create_server()
    _register_builtin_tools(server)
    context = Context.create("eval-catalog", "tools/list", server.lifespan_state)
    catalog = (await server.tools.list_tools(context))["tools"]

    names = [tool["name"] for tool in catalog]
    descriptions = [tool["description"].strip().casefold() for tool in catalog]
    assert len(names) == len(set(names))
    assert len(descriptions) == len(set(descriptions))
    assert all(
        tool["inputSchema"].get("additionalProperties") is False for tool in catalog
    )
