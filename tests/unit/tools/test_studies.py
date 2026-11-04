"""Study handles preserve immutable inputs and session ownership."""

import asyncio
from dataclasses import replace
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


async def test_snapshot_survives_source_replacement_and_is_owned_by_session(
    study_context, bridge, tmp_path
):
    source = tmp_path / "study.superdf"
    source.write_bytes(b"original bundle")
    owner = object()
    study_context._session = owner
    opened = await studies.open_study(study_context, {"file_path": str(source)})
    handle = opened["handle"]
    snapshot = study_context.lifespan.studies[handle]
    source.write_bytes(b"changed source")
    assert snapshot.content == b"original bundle"
    current = await studies.inspect_study(study_context, {"handle": handle})
    assert current["bundle_sha256"] == opened["bundle_sha256"]
    assert bridge.call_args.kwargs["full_precision"] is True
    assert not Path(bridge.call_args.args[1]["path"]).exists()
    other = Context.create("other", "tools/call", study_context.lifespan)
    other._session = object()
    denied = await studies.inspect_study(other, {"handle": handle})
    assert denied["ok"] is False
    assert denied["issues"][0]["code"] == "unknown_study"
    study_context.lifespan.studies[handle] = replace(snapshot, content=b"tampered")
    damaged = await studies.inspect_study(study_context, {"handle": handle})
    assert damaged["issues"][0]["code"] == "integrity_failure"


async def test_authorization_and_size_limit_precede_r(
    study_context, bridge, tmp_path, monkeypatch
):
    outside = tmp_path.parent / "outside.superdf"
    with pytest.raises(VFSError):
        await studies.open_study(study_context, {"file_path": str(outside)})
    bridge.assert_not_called()
    monkeypatch.setattr(studies, "MAX_BUNDLE_BYTES", 2)
    source = tmp_path / "large.superdf"
    source.write_bytes(b"abc")
    rejected = await studies.open_study(study_context, {"file_path": str(source)})
    assert rejected["issues"][0]["code"] == "bundle_too_large"
    bridge.assert_not_called()


async def test_failed_open_is_not_registered_and_limit_does_not_evict(
    study_context, bridge, tmp_path, monkeypatch
):
    source = tmp_path / "study.superdf"
    source.write_bytes(b"bundle")
    bridge.return_value = {"ok": False, "issues": [{"code": "missing_dependency"}]}
    failed = await studies.open_study(study_context, {"file_path": str(source)})
    assert "handle" not in failed
    assert not study_context.lifespan.studies
    bridge.return_value = {"ok": True, "issues": []}
    monkeypatch.setattr(studies, "MAX_STUDIES", 1)
    first = await studies.open_study(study_context, {"file_path": str(source)})
    again = await studies.open_study(study_context, {"file_path": str(source)})
    assert again["handle"] == first["handle"]
    source.write_bytes(b"second bundle")
    rejected = await studies.open_study(study_context, {"file_path": str(source)})
    assert rejected["issues"][0]["code"] == "study_limit"
    assert list(study_context.lifespan.studies) == [first["handle"]]


async def test_large_metadata_does_not_escape_into_shared_result_cache(
    study_context, bridge, tmp_path
):
    source = tmp_path / "study.superdf"
    source.write_bytes(b"bundle")
    bridge.return_value = {
        "ok": True,
        "issues": [],
        "context": {"notes": "x" * studies.MAX_RESULT_BYTES},
    }
    rejected = await studies.open_study(study_context, {"file_path": str(source)})
    assert rejected["issues"][0]["code"] == "result_too_large"
    assert not study_context.lifespan.studies


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
            {"handle": "study_" + "a" * 32, "analysis": analysis},
            studies._ANALYSIS_INPUT,
        )


async def test_sdk_sessions_cannot_reuse_each_others_studies(bridge, tmp_path):
    source = tmp_path / "study.superdf"
    source.write_bytes(b"bundle")
    server = create_server()
    server.configure(allowed_paths=[str(tmp_path)], read_only=True)
    register_tool_functions(server.tools, studies.open_study, studies.inspect_study)
    sdk_server = build_sdk_server(server).sdk_server
    async with create_connected_server_and_client_session(sdk_server) as first:
        opened = await first.call_tool("open_study", {"file_path": str(source)})
        first_payload = opened.model_dump(mode="json", by_alias=True)[
            "structuredContent"
        ]
        assert first_payload["ok"]
        handle = first_payload["handle"]
        async with create_connected_server_and_client_session(sdk_server) as second:
            rejected = await second.call_tool("inspect_study", {"handle": handle})
            second_payload = rejected.model_dump(mode="json", by_alias=True)[
                "structuredContent"
            ]
            assert second_payload["issues"][0]["code"] == "unknown_study"
        inspected = await first.call_tool("inspect_study", {"handle": handle})
        assert inspected.model_dump(mode="json", by_alias=True)["structuredContent"][
            "ok"
        ]


async def test_simultaneous_duplicate_opens_share_one_snapshot(
    study_context, bridge, tmp_path, monkeypatch
):
    source = tmp_path / "study.superdf"
    source.write_bytes(b"bundle")
    both_started = asyncio.Event()
    arrivals = 0

    async def inspect(*args, **kwargs):
        nonlocal arrivals
        arrivals += 1
        if arrivals == 2:
            both_started.set()
        await both_started.wait()
        return {"ok": True, "issues": []}

    bridge.side_effect = inspect
    monkeypatch.setattr(studies, "MAX_STUDIES", 1)
    first, second = await asyncio.gather(
        studies.open_study(study_context, {"file_path": str(source)}),
        studies.open_study(study_context, {"file_path": str(source)}),
    )
    assert first["ok"] and second["ok"]
    assert first["handle"] == second["handle"]
    assert len(study_context.lifespan.studies) == 1
