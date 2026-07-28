#!/usr/bin/env python3
"""Concurrency limiting for R subprocesses.

Regression cover for a module-level ``asyncio.Semaphore`` that bound itself to
whichever event loop first made a caller wait, then raised "bound to a different
event loop" in every loop afterwards.
"""

import asyncio
from shutil import which

import pytest

pytestmark = pytest.mark.skipif(
    which("R") is None, reason="R binary is required for concurrency tests"
)

from rmcp.config import get_config
from rmcp.r_integration import execute_r_script_async, get_r_semaphore

SCRIPT = "result <- list(value = 1)"


def _oversubscribed() -> int:
    """More concurrent calls than permits, so some must queue and wait."""
    return get_config().r.max_concurrent + 2


def test_semaphore_survives_a_second_event_loop():
    """Queueing in one loop must not poison the next one.

    Waiting is what binds the semaphore, so each round has to oversubscribe.
    """

    async def round_trip():
        results = await asyncio.gather(
            *[execute_r_script_async(SCRIPT, {}) for _ in range(_oversubscribed())],
            return_exceptions=True,
        )
        return [r for r in results if isinstance(r, BaseException)]

    first = asyncio.run(round_trip())
    assert not first, f"errors in first loop: {first}"

    # A fresh loop, exactly as a second asyncio.run() in a test suite creates.
    second = asyncio.run(round_trip())
    assert not second, f"errors after switching event loop: {second}"

    third = asyncio.run(round_trip())
    assert not third, f"errors in third loop: {third}"


def test_each_event_loop_gets_its_own_semaphore():
    async def grab():
        return get_r_semaphore()

    first = asyncio.run(grab())
    second = asyncio.run(grab())
    assert first is not second, "semaphore must not be shared across loops"


@pytest.mark.asyncio
async def test_semaphore_is_stable_within_one_loop():
    assert get_r_semaphore() is get_r_semaphore()


@pytest.mark.asyncio
async def test_concurrency_is_actually_capped():
    """The limiter must still limit -- not just avoid raising."""
    limit = get_config().r.max_concurrent
    live = 0
    peak = 0

    async def occupy():
        nonlocal live, peak
        async with get_r_semaphore():
            live += 1
            peak = max(peak, live)
            await asyncio.sleep(0.01)
            live -= 1

    await asyncio.gather(*[occupy() for _ in range(limit * 3)])
    assert peak == limit, f"expected peak {limit}, got {peak}"
