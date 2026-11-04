"""Actual R bundles through the official MCP client, alongside legacy tools."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture(scope="module")
def study_files(tmp_path_factory):
    probe = "quit(status=if (requireNamespace('superdf',quietly=TRUE) && packageVersion('superdf') >= '0.3.0' && all(vapply(c('arrow','survey','estimatr','zip'),requireNamespace,logical(1),quietly=TRUE))) 0L else 1L)"
    ready = (
        shutil.which("Rscript")
        and subprocess.run(["Rscript", "-e", probe], capture_output=True).returncode
        == 0
    )
    if not ready:
        if os.environ.get("RMCP_REQUIRE_STUDY_TESTS") == "1":
            pytest.fail(
                "Install R superdf >= 0.3.0, arrow, survey, estimatr, and zip for required study tests"
            )
        pytest.skip("Optional study integration dependencies are not installed")
    directory = tmp_path_factory.mktemp("study-protocol")
    script = r"""
library(superdf)
source(system.file('examples', 'simulated_study.R', package='superdf'))
root <- commandArgs(trailingOnly=TRUE)[[1]]
x <- collect_study(simulate_population())
write_superdf(x, file.path(root, 'study.superdf'))
write_superdf(x[-1, ], file.path(root, 'restricted.superdf'))
unknown <- superdf(as.data.frame(x), 'id', 'pupil', 'unknown_roster', assignments=context(x)$assignments)
write_superdf(unknown, file.path(root, 'unknown-roster.superdf'))
rejected <- check_analysis(x[-1, ], analysis_request('effect','followup',assignment='school_offer'))
writeLines(jsonlite::toJSON(rejected$issues, auto_unbox=TRUE, digits=NA), file.path(root,'issues.json'))
writeLines(jsonlite::toJSON(analyze_study(x)$table, dataframe='rows', digits=NA), file.path(root, 'expected.json'))
"""
    subprocess.run(
        ["Rscript", "-e", script, str(directory)], check=True, capture_output=True
    )
    return directory


async def test_study_protocol_and_existing_route(study_files):
    root = Path(__file__).resolve().parents[3]
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "rmcp.cli", "start"],
        cwd=str(study_files),
        env={**os.environ, "PYTHONPATH": str(root)},
    )
    expected = json.loads((study_files / "expected.json").read_text())
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments):
                response = await session.call_tool(name, arguments)
                payload = response.model_dump(mode="json", by_alias=True)
                assert not payload.get("isError", False), payload
                return payload["structuredContent"]

            names = {t.name for t in (await session.list_tools()).tools}
            assert {
                "open_study",
                "inspect_study",
                "check_study_analysis",
                "run_study_analysis",
                "linear_model",
                "read_csv",
            } <= names
            opened = await call(
                "open_study", {"file_path": str(study_files / "study.superdf")}
            )
            assert opened["ok"], opened
            handle = opened["handle"]
            assert opened["study"]["current_rows"] == 96
            requests = [
                {"kind": "mean", "outcome": "baseline", "weight": "sample_weight"},
                {
                    "kind": "effect",
                    "outcome": "followup",
                    "assignment": "school_offer",
                },
            ]
            for request, oracle in zip(requests, expected, strict=True):
                arguments = {"handle": handle, "analysis": request}
                checked = await call("check_study_analysis", arguments)
                assert checked["ok"], checked
                assert checked["validation_method"] == "requirements_check"
                assert "estimate" not in checked
                result = await call("run_study_analysis", arguments)
                assert result["ok"], result
                for actual, reference in (
                    ("value", "estimate"),
                    ("standard_error", "se"),
                    ("lower", "lower"),
                    ("upper", "upper"),
                ):
                    assert result["estimate"][actual] == pytest.approx(
                        oracle[reference], rel=1e-12, abs=1e-12
                    )
                assert result["bundle_sha256"] == opened["bundle_sha256"]
                analysis = result["receipt"]["analysis"]
                assert "current_keys" not in analysis
                assert analysis["roster"] == opened["study"]["roster"]
                assert result["receipt"]["declarations_verified"] is False
                for key, value in request.items():
                    assert analysis["request"][key] == value
                assert analysis["evidence"]
            missing_weight = await call(
                "check_study_analysis",
                {
                    "handle": handle,
                    "analysis": {
                        "kind": "mean",
                        "outcome": "baseline",
                        "weight": "unknown",
                    },
                },
            )
            assert missing_weight["ok"] is False
            assert "weight_required" in {
                issue["code"] for issue in missing_weight["issues"]
            }
            assert "estimate" not in missing_weight
            # Existing handlers and result shape remain the ordinary-table route.
            legacy = await call(
                "linear_model",
                {"data": {"x": [1, 2, 3, 4], "y": [3, 5, 7, 9]}, "formula": "y ~ x"},
            )
            assert legacy["coefficients"]["x"] == pytest.approx(2)
            assert "receipt" not in legacy
            restricted = await call(
                "open_study", {"file_path": str(study_files / "restricted.superdf")}
            )
            refused = await call(
                "run_study_analysis",
                {"handle": restricted["handle"], "analysis": requests[1]},
            )
            assert refused["ok"] is False
            assert all(
                issue["code"] and issue["category"] and "remedy" in issue
                for issue in refused["issues"]
            )
            assert "analysis_failed" not in {
                issue["code"] for issue in refused["issues"]
            }
            assert refused["issues"] == json.loads(
                (study_files / "issues.json").read_text()
            )
            assert "estimate" not in refused
            undeclared = await call(
                "open_study", {"file_path": str(study_files / "unknown-roster.superdf")}
            )
            for name in ("check_study_analysis", "run_study_analysis"):
                missing_roster = await call(
                    name, {"handle": undeclared["handle"], "analysis": requests[1]}
                )
                assert missing_roster["ok"] is False
                assert "randomized_roster_required" in {
                    issue["code"] for issue in missing_roster["issues"]
                }
                assert "estimate" not in missing_roster
            unknown = await call("inspect_study", {"handle": "study_" + "0" * 32})
            assert unknown["issues"][0]["code"] == "unknown_study"
