"""Small helpers shared by tests."""

import asyncio
import time
from collections.abc import Callable


async def wait_until(predicate: Callable[[], bool], within: float, step: float = 0.02) -> float:
    """Poll until predicate() is true. Returns seconds waited; fails the test on timeout."""
    start = time.monotonic()
    while not predicate():
        if time.monotonic() - start > within:
            raise AssertionError(f"condition not met within {within} s")
        await asyncio.sleep(step)
    return time.monotonic() - start
