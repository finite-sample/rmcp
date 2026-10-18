"""Progress from R reaches the client without being charged to the R timeout.

The runner used to await each progress notice while reading R's stderr, inside the
timed section. A client slower to accept a notice than the timeout turned a finished
script into a timeout, and the cleanup then signaled the exited R process and raised
``ProcessLookupError`` with an empty message.
"""

import asyncio
import time
from shutil import which

import pytest

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for progress tests"
)

from rmcp.r_integration import RExecutionError, execute_r_script_async  # noqa: E402

SCRIPT = 'rmcp_progress("halfway", 1, 2); rmcp_progress("done", 2, 2); result <- list(value = 1)'


class SlowClient:
    """Takes longer to accept each notice than the runner's timeout allows."""

    def __init__(self, delay: float):
        self.delay = delay
        self.received: list[tuple] = []

    async def progress(self, message, current, total):
        await asyncio.sleep(self.delay)
        self.received.append((message, current, total))

    async def info(self, message):
        self.received.append((message,))


def test_a_slow_client_does_not_time_out_a_finished_script():
    client = SlowClient(delay=1.5)

    result = asyncio.run(execute_r_script_async(SCRIPT, {}, client, timeout=1))

    assert result == {"value": 1}
    assert client.received == [("halfway", 1, 2), ("done", 2, 2)]


def test_a_script_that_overruns_still_reports_a_timeout():
    with pytest.raises(RExecutionError, match="timed out"):
        asyncio.run(
            execute_r_script_async(
                "Sys.sleep(5); result <- list()", {}, SlowClient(0), timeout=1
            )
        )


class StuckClient:
    """Never accepts a progress notice."""

    async def progress(self, message, current, total):
        await asyncio.Event().wait()

    async def info(self, message):
        await asyncio.Event().wait()


class SelfCancellingClient:
    async def progress(self, message, current, total):
        raise asyncio.CancelledError

    async def info(self, message):
        raise asyncio.CancelledError


def test_a_client_that_never_accepts_progress_cannot_hold_the_result(monkeypatch):
    from rmcp import r_integration

    monkeypatch.setattr(r_integration, "NOTICE_DRAIN_SECONDS", 0.5)
    started = time.monotonic()

    result = asyncio.run(execute_r_script_async(SCRIPT, {}, StuckClient(), timeout=5))

    assert result == {"value": 1}
    assert time.monotonic() - started < 4


def test_a_callback_that_raises_cancelled_error_does_not_cancel_the_run():
    result = asyncio.run(
        execute_r_script_async(SCRIPT, {}, SelfCancellingClient(), timeout=5)
    )

    assert result == {"value": 1}


def test_r_is_not_left_running_when_reading_its_output_fails(monkeypatch):
    # A stderr line longer than the stream buffer makes readline() raise inside the
    # task group; before, only timeouts and cancellation stopped R.
    from rmcp import r_integration

    started = []
    real_exec = asyncio.create_subprocess_exec

    async def recording_exec(*args, **kwargs):
        started.append(await real_exec(*args, **kwargs))
        return started[-1]

    monkeypatch.setattr(r_integration.asyncio, "create_subprocess_exec", recording_exec)
    script = 'message(strrep("x", 200000)); Sys.sleep(30); result <- list()'

    with pytest.raises(ExceptionGroup):  # the reader's ValueError, grouped
        asyncio.run(execute_r_script_async(script, {}, SlowClient(0), timeout=60))

    assert started and started[0].returncode is not None
