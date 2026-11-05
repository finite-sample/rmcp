"""Precision opt-in preserves ordinary R output and both async call paths."""

import math
from shutil import which

import pytest
from rmcp.r_integration import execute_r_script_async

pytestmark = pytest.mark.skipif(which("R") is None, reason="R is required")


@pytest.mark.parametrize("with_context", [False, True])
@pytest.mark.parametrize("full_precision", [False, True])
@pytest.mark.parametrize("preserve_nulls", [False, True])
async def test_r_json_precision(
    with_context, full_precision, preserve_nulls, context_factory, server_factory
):
    context = context_factory(server_factory()) if with_context else None
    result = await execute_r_script_async(
        "result <- list(value = pi, absent = NULL)",
        {},
        context=context,
        full_precision=full_precision,
        preserve_nulls=preserve_nulls,
    )
    expected = math.pi if full_precision else 3.1416
    assert result["value"] == pytest.approx(expected, rel=1e-14, abs=1e-14)
    assert result["absent"] == (None if preserve_nulls else {})
