"""R tools hand their request context to the R runner.

The runner forwards a script's ``RMCP_PROGRESS:`` lines and messages to the client only
through that context; a tool that drops it runs silently. Most tools did.
"""

import pytest
from rmcp.tools import descriptive, fileops


class _Context:
    async def info(self, *_args, **_kwargs):
        return None

    async def error(self, *_args, **_kwargs):
        return None


@pytest.mark.parametrize(
    ("module", "tool", "params"),
    [
        (descriptive, "summary_stats", {"data": {"x": [1, 2, 3]}}),
        (fileops, "data_info", {"data": {"x": [1, 2, 3]}}),
    ],
)
async def test_the_tool_passes_its_context_to_the_r_runner(
    module, tool, params, monkeypatch
):
    seen = []

    async def fake_runner(script, args, context=None, timeout=None):
        seen.append(context)
        return {}

    monkeypatch.setattr(module, "execute_r_script_async", fake_runner)
    context = _Context()

    await getattr(module, tool)(context, params)

    assert seen == [context]
