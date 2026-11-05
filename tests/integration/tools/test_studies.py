"""Actual R bundles through the official MCP client, alongside legacy tools."""

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture(scope="module")
def study_files(tmp_path_factory):
    probe = "quit(status=if (requireNamespace('studyframe',quietly=TRUE) && packageVersion('studyframe') >= '0.3.0' && all(vapply(c('arrow','survey','estimatr','zip'),requireNamespace,logical(1),quietly=TRUE))) 0L else 1L)"
    ready = (
        shutil.which("Rscript")
        and subprocess.run(["Rscript", "-e", probe], capture_output=True).returncode
        == 0
    )
    if not ready:
        if os.environ.get("RMCP_REQUIRE_STUDY_TESTS") == "1":
            pytest.fail(
                "Install R studyframe >= 0.3.0, arrow, survey, estimatr, and zip for required study tests"
            )
        pytest.skip("Optional study integration dependencies are not installed")
    directory = tmp_path_factory.mktemp("study-protocol")
    script = r"""
library(studyframe)
source(system.file('examples', 'simulated_study.R', package='studyframe'))
root <- commandArgs(trailingOnly=TRUE)[[1]]
x <- collect_study(simulate_population())
write_studyframe(x, file.path(root, 'study.studyframe'))
write_studyframe(x[-1, ], file.path(root, 'restricted.studyframe'))
unknown <- studyframe(as.data.frame(x), 'id', 'pupil', 'unknown_roster', assignments=context(x)$assignments)
write_studyframe(unknown, file.path(root, 'unknown-roster.studyframe'))
rejected <- check_analysis(x[-1, ], analysis_request('effect','followup',assignment='school_offer'))
writeLines(jsonlite::toJSON(rejected$issues, auto_unbox=TRUE, digits=NA), file.path(root,'issues.json'))
writeLines(jsonlite::toJSON(analyze_study(x)$table, dataframe='rows', digits=NA), file.path(root, 'expected.json'))
bundled <- read_studyframe(file.path(root, 'study.studyframe'))
requests <- list(analysis_request('mean', 'baseline', weight='sample_weight'), analysis_request('effect', 'followup', assignment='school_offer'))
receipts <- lapply(requests, function(request) {
  analysis <- run_analysis(bundled, request)$analysis
  analysis$current_keys <- NULL
  analysis
})
writeLines(jsonlite::toJSON(receipts, auto_unbox=TRUE, digits=NA, null='null'), file.path(root, 'receipts.json'))
wide_data <- data.frame(id=1:3)
for (i in seq_len(200)) wide_data[[paste0('question_', i)]] <- seq_len(3)
wide <- studyframe(wide_data, 'id', 'person', 'wide_questionnaire', variables=lapply(names(wide_data), function(column) variable_spec(column, label=paste(rep('Question wording', 10), collapse=' '))))
write_studyframe(wide, file.path(root, 'wide.studyframe'))
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
    receipts = json.loads((study_files / "receipts.json").read_text())
    with zipfile.ZipFile(study_files / "study.studyframe") as bundle:
        expected_context = json.loads(bundle.read("context.json"))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments):
                response = await session.call_tool(name, arguments)
                payload = response.model_dump(mode="json", by_alias=True)
                assert not payload.get("isError", False), payload
                return payload["structuredContent"]

            names = {t.name for t in (await session.list_tools()).tools}
            assert "open_study" not in names
            assert {
                "inspect_study",
                "check_study_analysis",
                "run_study_analysis",
                "linear_model",
                "read_csv",
            } <= names
            opened = await call(
                "inspect_study", {"file_path": str(study_files / "study.studyframe")}
            )
            assert opened["ok"], opened
            study_ref = opened["study_ref"]
            assert opened["context"] == expected_context
            assert opened["study"]["current_rows"] == 96
            wide = await call(
                "inspect_study", {"file_path": str(study_files / "wide.studyframe")}
            )
            assert wide["ok"], wide
            assert len(wide["context"]["variables"]) == 201
            assert len(json.dumps(wide).encode()) > 50 * 1024
            requests = [
                {"kind": "mean", "outcome": "baseline", "weight": "sample_weight"},
                {
                    "kind": "effect",
                    "outcome": "followup",
                    "assignment": "school_offer",
                },
            ]
            for request, oracle, receipt in zip(
                requests, expected, receipts, strict=True
            ):
                arguments = {"study_ref": study_ref, "analysis": request}
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
                assert result["study_ref"] == study_ref
                assert '"current_keys"' not in json.dumps(result)
                assert '"fit"' not in json.dumps(result)
                analysis = result["receipt"]["analysis"]
                assert analysis == receipt
                assert "current_keys" not in analysis
                assert analysis["roster"] == opened["study"]["roster"]
                assert result["receipt"]["declarations_verified"] is False
                for key, value in request.items():
                    assert analysis["request"][key] == value
                assert analysis["evidence"]
            missing_weight = await call(
                "check_study_analysis",
                {
                    "study_ref": study_ref,
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
                {"data": {"x": [1, 2, 3, 4], "y": [3, 5, 6, 9]}, "formula": "y ~ x"},
            )
            assert legacy["coefficients"]["x"] == pytest.approx(1.9)
            assert "receipt" not in legacy
            restricted = await call(
                "inspect_study",
                {"file_path": str(study_files / "restricted.studyframe")},
            )
            refused = await call(
                "run_study_analysis",
                {"study_ref": restricted["study_ref"], "analysis": requests[1]},
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
                "inspect_study",
                {"file_path": str(study_files / "unknown-roster.studyframe")},
            )
            for name in ("check_study_analysis", "run_study_analysis"):
                missing_roster = await call(
                    name,
                    {"study_ref": undeclared["study_ref"], "analysis": requests[1]},
                )
                assert missing_roster["ok"] is False
                assert "randomized_roster_required" in {
                    issue["code"] for issue in missing_roster["issues"]
                }
                assert "estimate" not in missing_roster
            changed = await call(
                "run_study_analysis",
                {
                    "study_ref": {**study_ref, "sha256": "0" * 64},
                    "analysis": requests[0],
                },
            )
            assert changed["issues"][0]["code"] == "study_changed"
            assert "estimate" not in changed


def test_study_client_runner(study_files, tmp_path):
    root = Path(__file__).resolve().parents[3]
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps({"kind": "mean", "outcome": "baseline", "weight": "sample_weight"})
    )
    output = tmp_path / "report.json"
    process = subprocess.run(
        [
            sys.executable,
            str(root / "examples/analyze_study.py"),
            str(study_files / "study.studyframe"),
            str(request),
            "--output",
            str(output),
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert process.returncode == 0, process.stderr
    report = json.loads(output.read_text())
    assert report["ok"]
    assert report["check"]["validation_method"] == "requirements_check"
    expected = json.loads((study_files / "expected.json").read_text())[0]
    assert report["run"]["estimate"]["value"] == pytest.approx(expected["estimate"])
    assert report["inspection"]["study_ref"] == report["run"]["study_ref"]
    request.write_text(
        json.dumps({"kind": "mean", "outcome": "baseline", "weight": "absent"})
    )
    output = tmp_path / "refused.json"
    process = subprocess.run(
        [
            sys.executable,
            str(root / "examples/analyze_study.py"),
            str(study_files / "study.studyframe"),
            str(request),
            "--output",
            str(output),
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert process.returncode == 1, process.stderr
    report = json.loads(output.read_text())
    assert not report["ok"]
    assert "run" not in report


def test_regression_client_runner(tmp_path):
    probe = "quit(status=if (requireNamespace('studyframe',quietly=TRUE) && 'regression_request' %in% getNamespaceExports('studyframe')) 0L else 1L)"
    ready = (
        shutil.which("Rscript")
        and subprocess.run(["Rscript", "-e", probe], capture_output=True).returncode
        == 0
    )
    if not ready:
        if os.environ.get("RMCP_REQUIRE_STUDY_REGRESSION") == "1":
            pytest.fail(
                "Install studyframe with regression_request() for regression protocol tests"
            )
        pytest.skip("Optional studyframe regression adapter is not installed")
    script = r"""
library(studyframe)
root <- commandArgs(trailingOnly=TRUE)[[1]]
data <- data.frame(id=1:40, respondent=rep(1:10, each=4), rank=rep(1:4, 10))
data$outcome <- 2 + data$rank/3 + sin(data$id) + data$respondent/10
x <- studyframe(data, 'id', 'recall', 'observed_recalls')
request <- regression_request('outcome', 'rank', cluster='respondent', se_type='stata', target='Observed recall records', assumptions='Independent respondent clusters and a linear conditional mean')
fit <- run_analysis(x, request)$fit
write_studyframe(x, file.path(root, 'study.studyframe'))
writeLines(jsonlite::toJSON(request, auto_unbox=TRUE, null='null'), file.path(root, 'request.json'))
expected <- data.frame(term=fit$term, value=fit$coefficients, standard_error=fit$std.error, lower=fit$conf.low, upper=fit$conf.high, p_value=fit$p.value, degrees_of_freedom=fit$df, row.names=NULL)
writeLines(jsonlite::toJSON(expected, dataframe='rows', digits=NA), file.path(root, 'expected.json'))
"""
    subprocess.run(
        ["Rscript", "-e", script, str(tmp_path)], check=True, capture_output=True
    )
    root = Path(__file__).resolve().parents[3]
    output = tmp_path / "receipt.json"
    process = subprocess.run(
        [
            sys.executable,
            str(root / "examples/analyze_study.py"),
            str(tmp_path / "study.studyframe"),
            str(tmp_path / "request.json"),
            "--output",
            str(output),
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert process.returncode == 0, process.stderr
    report = json.loads(output.read_text())
    assert report["ok"]
    expected = json.loads((tmp_path / "expected.json").read_text())
    actual = report["run"]["estimate"]["coefficients"]
    assert len(actual) == len(expected) == 2
    for coefficient, reference in zip(actual, expected, strict=True):
        assert coefficient["term"] == reference["term"]
        for field in reference.keys() - {"term"}:
            assert coefficient[field] == pytest.approx(
                reference[field], rel=1e-12, abs=1e-12
            )
    analysis = report["run"]["receipt"]["analysis"]
    assert analysis["inference"] == "model_based_association"
    assert analysis["request"]["target"] == "Observed recall records"
    assert "current_keys" not in analysis


async def test_missing_studyframe_keeps_ordinary_tools_working(tmp_path):
    if shutil.which("Rscript") is None:
        if os.environ.get("RMCP_REQUIRE_NO_STUDYFRAME") == "1":
            pytest.fail("R is required for the missing-studyframe protocol test")
        pytest.skip("R is not installed")
    probe = subprocess.run(
        [
            "Rscript",
            "-e",
            "quit(status=if (requireNamespace('studyframe', quietly=TRUE)) 0L else 1L)",
        ],
        capture_output=True,
    )
    if probe.returncode == 0:
        if os.environ.get("RMCP_REQUIRE_NO_STUDYFRAME") == "1":
            pytest.fail("Run the missing-dependency test before installing studyframe")
        pytest.skip("This test requires an R library without studyframe")
    source = tmp_path / "unavailable.studyframe"
    source.write_bytes(b"Dependency validation must precede bundle parsing")
    root = Path(__file__).resolve().parents[3]
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "rmcp.cli", "start"],
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": str(root)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await session.call_tool(
                "inspect_study", {"file_path": str(source)}
            )
            payload = response.model_dump(mode="json", by_alias=True)
            assert not payload.get("isError", False), payload
            rejected = payload["structuredContent"]
            assert rejected["ok"] is False
            assert "study_ref" not in rejected
            assert rejected["issues"][0]["code"] == "missing_dependency"
            assert rejected["issues"][0]["category"] == "dependency"
            assert "studyframe" in rejected["issues"][0]["message"]
            response = await session.call_tool(
                "linear_model",
                {"data": {"x": [1, 2, 3, 4], "y": [3, 5, 6, 9]}, "formula": "y ~ x"},
            )
            payload = response.model_dump(mode="json", by_alias=True)
            assert not payload.get("isError", False), payload
            ordinary = payload["structuredContent"]
            assert ordinary["coefficients"]["x"] == pytest.approx(1.9)
            assert "receipt" not in ordinary
