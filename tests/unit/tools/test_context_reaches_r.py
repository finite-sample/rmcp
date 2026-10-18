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


@pytest.mark.parametrize("include_image", [True, False])
async def test_the_image_runner_forwards_context(include_image, monkeypatch):
    from rmcp import r_integration

    seen = []

    async def fake_runner(script, args, context=None, timeout=None):
        seen.append(context)
        return {}

    monkeypatch.setattr(r_integration, "execute_r_script_async", fake_runner)
    context = _Context()

    await r_integration.execute_r_script_with_image_async(
        "result <- list()", {}, include_image=include_image, context=context
    )

    assert seen == [context]


async def test_a_plotting_tool_passes_its_context_to_the_image_runner(monkeypatch):
    from rmcp.tools import visualization

    seen = []

    async def fake_image_runner(script, args, **kwargs):
        seen.append(kwargs.get("context"))
        return {}

    monkeypatch.setattr(
        visualization, "execute_r_script_with_image_async", fake_image_runner
    )
    context = _Context()

    await visualization.scatter_plot(
        context, {"data": {"x": [1, 2, 3], "y": [2, 4, 6]}, "x": "x", "y": "y"}
    )

    assert seen == [context]
