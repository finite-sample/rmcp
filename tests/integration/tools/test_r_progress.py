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


class StubbornClient:
    """Its notice handler keeps running through cancellation."""

    async def progress(self, message, current, total):
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(10)

    async def info(self, message):
        await self.progress(message, None, None)


def test_a_callback_resisting_cancellation_cannot_hold_the_result(monkeypatch):
    from rmcp import r_integration

    monkeypatch.setattr(r_integration, "NOTICE_DRAIN_SECONDS", 0.5)
    monkeypatch.setattr(r_integration, "SENDER_STOP_SECONDS", 0.5)

    async def run():
        started = time.monotonic()
        result = await execute_r_script_async(SCRIPT, {}, StubbornClient(), timeout=5)
        return result, time.monotonic() - started

    result, elapsed = asyncio.run(run())

    assert result == {"value": 1}
    assert elapsed < 4


def test_draining_notices_does_not_hold_the_r_slot(monkeypatch):
    # One R slot. A's client never accepts notices, so A drains for the full
    # bound after R exits; B must get the slot as soon as A's R is done.
    from rmcp import r_integration

    monkeypatch.setattr(r_integration, "NOTICE_DRAIN_SECONDS", 2.0)

    async def run():
        slot = asyncio.Semaphore(1)
        monkeypatch.setattr(r_integration, "get_r_semaphore", lambda: slot)
        started = time.monotonic()
        a = asyncio.create_task(
            execute_r_script_async(SCRIPT, {}, StuckClient(), timeout=10)
        )
        await asyncio.sleep(0.05)
        b_result = await execute_r_script_async("result <- list(value = 2)", {})
        b_done = time.monotonic() - started
        a_result = await a
        return a_result, b_result, b_done, time.monotonic() - started

    a_result, b_result, b_done, a_done = asyncio.run(run())

    assert (a_result, b_result) == ({"value": 1}, {"value": 2})
    assert b_done < a_done - 1


def test_a_flood_of_progress_keeps_the_latest_notice(monkeypatch):
    from rmcp import r_integration

    monkeypatch.setattr(r_integration, "NOTICE_QUEUE_SIZE", 5)
    client = SlowClient(delay=0.01)
    flood = (
        'for (i in 1:2000) rmcp_progress("step", i, 2000); result <- list(value = 1)'
    )

    result = asyncio.run(execute_r_script_async(flood, {}, client, timeout=30))

    assert result == {"value": 1}
    assert len(client.received) < 2000
    assert client.received[-1] == ("step", 2000, 2000)


def test_canceling_during_the_drain_stops_the_sender(monkeypatch):
    from rmcp import r_integration

    monkeypatch.setattr(r_integration, "NOTICE_DRAIN_SECONDS", 5.0)

    async def run():
        before = set(asyncio.all_tasks())
        runner = asyncio.create_task(
            execute_r_script_async(SCRIPT, {}, StuckClient(), timeout=10)
        )
        await asyncio.sleep(1.5)  # R has finished; the runner is draining
        runner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await runner
        await asyncio.sleep(0)
        return [
            t for t in asyncio.all_tasks() - before if t is not asyncio.current_task()
        ]

    assert asyncio.run(run()) == []


def test_progress_lines_are_not_kept_with_stderr(monkeypatch):
    # A script that floods progress and then fails reports only its real stderr.
    flood = 'for (i in 1:5000) rmcp_progress("step", i, 5000); stop("boom")'

    with pytest.raises(RExecutionError) as raised:
        asyncio.run(execute_r_script_async(flood, {}, SlowClient(0), timeout=30))

    assert "RMCP_PROGRESS" not in raised.value.stderr
    assert "boom" in raised.value.stderr
