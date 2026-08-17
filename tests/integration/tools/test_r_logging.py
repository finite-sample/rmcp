"""Privacy checks for R execution diagnostics."""

from shutil import which

import pytest
from rmcp.r_integration import execute_r_script, execute_r_script_async

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for R logging tests"
)


def test_sync_r_execution_logs_metadata_without_values(capsys):
    secret = "private-r-input-value-sync-82f1"

    result = execute_r_script("result <- list(answer = args$value)", {"value": secret})
    logs = "\n".join(capsys.readouterr())

    assert result == {"answer": secret}
    assert secret not in logs
    assert "argument_count" in logs
    assert "argument_keys" in logs
    assert "result_keys" in logs


async def test_async_r_execution_logs_metadata_without_values(capsys):
    secret = "private-r-input-value-async-a56c"

    result = await execute_r_script_async(
        "result <- list(answer = args$value)", {"value": secret}
    )
    logs = "\n".join(capsys.readouterr())

    assert result == {"answer": secret}
    assert secret not in logs
    assert "argument_count" in logs
    assert "argument_keys" in logs
    assert "result keys" in logs
