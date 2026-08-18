"""Tests for cross-field MCP tool contract validation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from rmcp.core.context import Context, LifespanState
from rmcp.core.schemas import SchemaError, formula_schema, table_schema, validate_schema
from rmcp.r_integration import RExecutionError
from rmcp.registries.tools import ToolsRegistry
from rmcp.security.vfs import VFS, VFSError


def test_table_contract_accepts_typed_equal_length_columns():
    validate_schema(
        {"x": [1, 2], "flag": [True, False], "label": ["a", None]},
        table_schema(),
        "data",
    )


@pytest.mark.parametrize("data", [{}, {"x": []}, {"x": [1, 2], "y": [3]}])
def test_table_contract_rejects_structurally_invalid_data(data):
    with pytest.raises(SchemaError):
        validate_schema(data, table_schema(), "data")


@pytest.mark.parametrize(
    "formula",
    [
        "y ~ x + z",
        "y ~ log(x) + I(z^2)",
        "y ~ x * factor(group)",
        "y ~ x | instrument",
    ],
)
def test_formula_contract_accepts_statistical_expressions(formula):
    validate_schema(formula, formula_schema(), "formula")


@pytest.mark.parametrize(
    "formula",
    [
        'y ~ system("true")',
        "y ~ base::log(x)",
        "y ~ source(x)",
        "y ~ .GlobalEnv$secret",
        "y ~ x; print(x)",
        "y ~ (system)(cmd)",
        "y ~ I(system)(cmd)",
    ],
)
def test_formula_contract_rejects_code_execution(formula):
    with pytest.raises(SchemaError):
        validate_schema(formula, formula_schema(), "formula")


def test_duplicate_tool_names_are_rejected():
    async def handler(context, params):
        return {}

    registry = ToolsRegistry()
    registry.register("duplicate", handler, {"type": "object"})

    with pytest.raises(ValueError, match="already registered"):
        registry.register("duplicate", handler, {"type": "object"})


def test_tool_contracts_reject_unknown_arguments_by_default():
    async def handler(context, params):
        return {}

    registry = ToolsRegistry()
    registry.register(
        "strict-input",
        handler,
        {"type": "object", "properties": {"value": {"type": "number"}}},
    )

    assert registry._tools["strict-input"].input_schema["additionalProperties"] is False


def test_vfs_validates_delegated_reads(tmp_path):
    allowed_file = tmp_path / "data.csv"
    allowed_file.write_text("x\n1\n", encoding="utf-8")
    context = Context.create(
        "read",
        "read_csv",
        LifespanState(vfs=VFS([tmp_path], read_only=True)),
    )

    assert context.require_read_path(allowed_file) == allowed_file.resolve()
    with pytest.raises(VFSError, match="Path access denied"):
        context.require_read_path("/etc/passwd")
    with pytest.raises(VFSError, match="Remote URL access is not permitted"):
        context.require_read_path("https://example.test/data.csv")


def test_vfs_stages_an_isolated_snapshot_for_delegated_reads(tmp_path):
    allowed_file = tmp_path / "data.csv"
    allowed_file.write_text("x\n1\n", encoding="utf-8")
    source_mtime_ns = 946_684_800_123_456_700
    allowed_file_stat = allowed_file.stat()
    os.utime(
        allowed_file,
        ns=(allowed_file_stat.st_atime_ns, source_mtime_ns),
    )
    context = Context.create(
        "read",
        "read_csv",
        LifespanState(vfs=VFS([tmp_path], read_only=True)),
    )

    with context.stage_read_path(allowed_file) as staged_path:
        assert staged_path != allowed_file
        assert staged_path.suffix == ".csv"
        allowed_file.write_text("x\n2\n", encoding="utf-8")
        assert staged_path.read_text(encoding="utf-8") == "x\n1\n"
        assert staged_path.stat().st_mtime_ns == source_mtime_ns

    assert not staged_path.exists()


def test_vfs_snapshot_preserves_requested_symlink_suffix(tmp_path):
    target = tmp_path / "extensionless-workbook"
    target.write_bytes(b"workbook")
    alias = tmp_path / "data.xlsx"
    alias.symlink_to(target.name)
    context = Context.create(
        "read",
        "read_excel",
        LifespanState(vfs=VFS([tmp_path], read_only=True)),
    )

    with context.stage_read_path(alias) as staged_path:
        assert staged_path.suffix == ".xlsx"
        assert staged_path.read_bytes() == b"workbook"


def test_windows_final_paths_are_normalized_and_confined(tmp_path):
    vfs = VFS([tmp_path], read_only=True)
    vfs.allowed_roots = [Path("C:/allowed")]

    assert (
        vfs._normalize_windows_final_path(r"\\?\C:\allowed\data.csv")
        == r"C:\allowed\data.csv"
    )
    assert (
        vfs._normalize_windows_final_path(r"\\?\UNC\server\share\data.csv")
        == r"\\server\share\data.csv"
    )
    assert vfs._windows_path_is_allowed(r"c:\ALLOWED\nested\data.csv")
    assert not vfs._windows_path_is_allowed(r"C:\allowed-neighbor\data.csv")


@pytest.mark.asyncio
async def test_tool_errors_do_not_expose_subprocess_environment():
    async def handler(context, params):
        raise RExecutionError(
            "R script failed with return code 1\n"
            "COMMAND: /usr/bin/R --file=/private/tmp/secret.R\n"
            "STDERR:\nunknown variable\n"
            "ENVIRONMENT:\n{'PATH': '/private/bin'}",
            stderr="unknown variable",
            returncode=1,
        )

    registry = ToolsRegistry()
    registry.register("fails", handler, {"type": "object"})
    context = Context.create("failure", "tools/call", LifespanState())

    response = await registry.call_tool(context, "fails", {})
    text = response["content"][0]["text"]
    assert text == "Tool execution error: R script execution failed"
    assert "ENVIRONMENT" not in text
    assert "/private" not in text


@pytest.mark.asyncio
async def test_vfs_errors_do_not_expose_configured_roots(tmp_path):
    async def handler(context, params):
        context.require_read_path(params["file_path"])
        return {}

    registry = ToolsRegistry()
    registry.register(
        "read",
        handler,
        {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        },
    )
    context = Context.create(
        "failure",
        "tools/call",
        LifespanState(vfs=VFS([tmp_path], read_only=True)),
    )

    response = await registry.call_tool(context, "read", {"file_path": "/etc/passwd"})
    text = response["content"][0]["text"]
    assert text == "Tool execution error: File access denied by virtual filesystem"
    assert str(tmp_path) not in text
    assert "Allowed roots" not in text


@pytest.mark.asyncio
async def test_enhanced_r_errors_do_not_expose_subprocess_details():
    async def handler(context, params):
        raise RExecutionError(
            "❌ Statistical Computation Error\n"
            "Original error: R script failed with return code 1\n"
            "COMMAND: /usr/local/bin/R --file=/private/tmp/secret.R\n"
            "STDERR:\nnot enough observations\n"
            "ENVIRONMENT:\n{'PATH': '/private/bin'}",
            stderr="not enough observations",
            returncode=1,
        )

    registry = ToolsRegistry()
    registry.register("fails", handler, {"type": "object"})
    context = Context.create("failure", "tools/call", LifespanState())

    response = await registry.call_tool(context, "fails", {})
    text = response["content"][0]["text"]
    assert text.startswith("Tool execution error: ❌ Statistical Computation Error")
    assert "Original error" not in text
    assert "COMMAND" not in text
    assert "ENVIRONMENT" not in text
    assert "/private" not in text
