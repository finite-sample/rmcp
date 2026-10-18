"""Progress from R reaches the client without being charged to the R timeout.

The runner used to await each progress notice while reading R's stderr, inside the
timed section. A client slower to accept a notice than the timeout turned a finished
script into a timeout, and the cleanup then signaled the exited R process and raised
``ProcessLookupError`` with an empty message.
"""

import asyncio
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
