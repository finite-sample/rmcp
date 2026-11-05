"""Study references authorize each call and bind inference to exact file bytes."""

import asyncio
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from rmcp.core.context import Context, LifespanState
from rmcp.core.schemas import SchemaError, validate_schema
from rmcp.core.sdk_adapter import build_sdk_server
from rmcp.core.server import create_server
from rmcp.registries.tools import register_tool_functions
from rmcp.security.vfs import VFS, VFSError
from rmcp.tools import studies

from tests.unit.core.test_sdk_adapter import create_connected_server_and_client_session

ANALYSIS = {"kind": "mean", "outcome": "y", "weight": "w"}


@pytest.fixture
def study_context(tmp_path):
    state = LifespanState(vfs=VFS([tmp_path]))
    return Context.create("study-test", "tools/call", state)


@pytest.fixture
def bridge(monkeypatch):
    execute = AsyncMock(
        return_value={"ok": True, "issues": [], "study": {"current_rows": 2}}
    )
    monkeypatch.setattr(studies, "execute_r_script_async", execute)
    return execute


def reference(path, content=b"bundle"):
    return {"file_path": str(path), "sha256": hashlib.sha256(content).hexdigest()}


async def test_inspect_returns_original_path_and_content_digest(
    study_context, bridge, tmp_path
):
    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")
    result = await studies.inspect_study(study_context, {"file_path": str(source)})
    assert result["study_ref"] == reference(source)
    assert result["bundle_sha256"] == reference(source)["sha256"]
    assert bridge.call_args.kwargs["full_precision"] is True
    assert not Path(bridge.call_args.args[1]["path"]).exists()


@pytest.mark.parametrize(
    "action", [studies.check_study_analysis, studies.run_study_analysis]
)
@pytest.mark.parametrize("change", ["file", "hash"])
async def test_changed_content_or_hash_is_rejected_before_r(
    study_context, bridge, tmp_path, action, change
):
    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")
    ref = reference(source)
    if change == "file":
        source.write_bytes(b"changed")
    else:
        ref["sha256"] = "0" * 64
    rejected = await action(study_context, {"study_ref": ref, "analysis": ANALYSIS})
    assert rejected["issues"][0]["code"] == "study_changed"
    assert "estimate" not in rejected
    bridge.assert_not_awaited()


@pytest.mark.parametrize(
    "action",
    [studies.inspect_study, studies.check_study_analysis, studies.run_study_analysis],
)
@pytest.mark.parametrize("path_kind", ["absolute", "traversal", "symlink"])
async def test_every_call_authorizes_the_path_even_with_valid_digest(
    bridge, tmp_path, action, path_kind
):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.studyframe"
    outside.write_bytes(b"bundle")
    path = outside
    if path_kind == "traversal":
        path = allowed / ".." / outside.name
    elif path_kind == "symlink":
        path = allowed / "link.studyframe"
        path.symlink_to(outside)
    context = Context.create("denied", "tools/call", LifespanState(vfs=VFS([allowed])))
    params = (
        {"file_path": str(path)}
        if action is studies.inspect_study
        else {"study_ref": reference(path), "analysis": ANALYSIS}
    )
    with pytest.raises(VFSError):
        await action(context, params)
    bridge.assert_not_awaited()


async def test_access_policy_is_rechecked_after_inspection(
    study_context, bridge, tmp_path
):
    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")
    inspected = await studies.inspect_study(study_context, {"file_path": str(source)})
    empty_root = tmp_path / "restricted"
    empty_root.mkdir()
    study_context.lifespan.vfs = VFS([empty_root])
    bridge.reset_mock()
    with pytest.raises(VFSError):
        await studies.run_study_analysis(
            study_context, {"study_ref": inspected["study_ref"], "analysis": ANALYSIS}
        )
    bridge.assert_not_awaited()


@pytest.mark.parametrize(
    "action",
    [studies.inspect_study, studies.check_study_analysis, studies.run_study_analysis],
)
async def test_bundle_size_limit_precedes_r(
    study_context, bridge, tmp_path, monkeypatch, action
):
    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")
    monkeypatch.setattr(studies, "MAX_BUNDLE_BYTES", 2)
    params = (
        {"file_path": str(source)}
        if action is studies.inspect_study
        else {"study_ref": reference(source), "analysis": ANALYSIS}
    )
    rejected = await action(study_context, params)
    assert rejected["issues"][0]["code"] == "bundle_too_large"
    bridge.assert_not_awaited()


async def test_r_receives_the_hashed_snapshot_when_source_changes(
    study_context, bridge, tmp_path
):
    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")

    async def execute(script, args, **kwargs):
        source.write_bytes(b"replaced after read")
        assert Path(args["path"]).read_bytes() == b"bundle"
        assert Path(args["path"]) != source
        return {"ok": True, "issues": []}

    bridge.side_effect = execute
    result = await studies.run_study_analysis(
        study_context, {"study_ref": reference(source), "analysis": ANALYSIS}
    )
    assert result["study_ref"] == reference(source)
    assert result["bundle_sha256"] == reference(source)["sha256"]
    assert not Path(bridge.call_args.args[1]["path"]).exists()


async def test_large_metadata_does_not_escape_into_shared_result_cache(
    study_context, bridge, tmp_path
):
    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")
    bridge.return_value = {
        "ok": True,
        "issues": [],
        "context": {"notes": "x" * studies.MAX_RESULT_BYTES},
    }
    result = await studies.inspect_study(study_context, {"file_path": str(source)})
    assert result["issues"][0]["code"] == "result_too_large"
    assert "study_ref" not in result


@pytest.mark.parametrize(
    "analysis",
    [
        {"kind": "mean", "outcome": "x;system('id')", "weight": "w"},
        {"kind": "mean", "outcome": "y", "weight": "w", "formula": "y~x"},
        {"kind": "effect", "outcome": "y", "assignment": "a;system('id')"},
        {
            "kind": "effect",
            "outcome": "y",
            "assignment": "a",
            "roster_assertion": {"complete": True, "source": " "},
        },
    ],
)
def test_analysis_schema_refuses_code_and_request_only_roster_claims(analysis):
    with pytest.raises(SchemaError):
        validate_schema(
            {"study_ref": reference("study.studyframe"), "analysis": analysis},
            studies._ANALYSIS_INPUT,
        )


@pytest.mark.parametrize(
    "ref",
    [
        {"file_path": "study.studyframe"},
        {"file_path": "study.studyframe", "sha256": "bad"},
    ],
)
def test_analysis_requires_a_valid_content_digest(ref):
    with pytest.raises(SchemaError):
        validate_schema(
            {"study_ref": ref, "analysis": ANALYSIS}, studies._ANALYSIS_INPUT
        )


async def test_reference_is_reusable_after_reconnect_to_a_new_server(bridge, tmp_path):
    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")
    ref = None
    for _ in range(2):
        server = create_server()
        server.configure(allowed_paths=[str(tmp_path)], read_only=True)
        register_tool_functions(
            server.tools, studies.inspect_study, studies.check_study_analysis
        )
        async with create_connected_server_and_client_session(
            build_sdk_server(server).sdk_server
        ) as session:
            if ref is None:
                result = await session.call_tool(
                    "inspect_study", {"file_path": str(source)}
                )
                ref = result.structured_content["study_ref"]
            result = await session.call_tool(
                "check_study_analysis", {"study_ref": ref, "analysis": ANALYSIS}
            )
            assert not result.is_error
            assert result.structured_content["ok"]
            assert result.structured_content["study_ref"] == ref


@pytest.mark.parametrize(
    "action",
    [studies.inspect_study, studies.check_study_analysis, studies.run_study_analysis],
)
async def test_context_without_vfs_still_enforces_allowed_paths(
    bridge, tmp_path, action
):
    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")
    state = LifespanState(allowed_paths=[tmp_path])
    context = Context.create("embedded", "tools/call", state)
    params = (
        {"file_path": str(source)}
        if action is studies.inspect_study
        else {"study_ref": reference(source), "analysis": ANALYSIS}
    )
    assert (await action(context, params))["ok"]
    state.allowed_paths = []
    bridge.reset_mock()
    with pytest.raises(VFSError):
        await action(context, params)
    bridge.assert_not_awaited()


@pytest.mark.parametrize(
    "error", [RuntimeError("backend failed"), asyncio.CancelledError()]
)
async def test_temporary_snapshot_is_removed_on_backend_error_or_cancellation(
    study_context, bridge, tmp_path, error
):
    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")
    bridge.side_effect = error
    with pytest.raises(type(error)):
        await studies.inspect_study(study_context, {"file_path": str(source)})
    assert not Path(bridge.call_args.args[1]["path"]).exists()


async def test_reference_preserves_original_relative_path(
    study_context, bridge, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    Path("study.studyframe").write_bytes(b"bundle")
    result = await studies.inspect_study(
        study_context, {"file_path": "study.studyframe"}
    )
    assert result["study_ref"] == reference("study.studyframe")


@pytest.mark.parametrize("stateless", [False, True])
async def test_reference_reuse_over_http_requests(bridge, tmp_path, stateless):
    from rmcp.transport.sdk import create_streamable_http_app

    from tests.utils import (
        initialize_streamable_session,
        parse_streamable_response,
        streamable_http_client,
    )

    source = tmp_path / "study.studyframe"
    source.write_bytes(b"bundle")
    server = create_server()
    server.configure(allowed_paths=[str(tmp_path)], read_only=True)
    register_tool_functions(
        server.tools, studies.inspect_study, studies.check_study_analysis
    )
    app = create_streamable_http_app(
        server, stateless=stateless, manage_server_lifecycle=False
    )
    async with streamable_http_client(app) as client:
        _, headers = await initialize_streamable_session(client)
        ref = None
        for request_id in (2, 3, 4):
            name = "inspect_study" if ref is None else "check_study_analysis"
            arguments = (
                {"file_path": str(source)}
                if ref is None
                else {"study_ref": ref, "analysis": ANALYSIS}
            )
            response = await client.post(
                "/mcp",
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
            )
            message = parse_streamable_response(response)
            assert "error" not in message, message
            result = message["result"]["structuredContent"]
            assert result["ok"], result
            if ref is None:
                ref = result["study_ref"]
            assert result["study_ref"] == ref
