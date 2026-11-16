"""Background tasks that cannot die quietly.

``spawn`` logs a task's exception the moment it ends with one (asyncio would otherwise keep it
until shutdown). ``cancel_all`` stops tasks and waits for all of them, even if some failed.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine, Iterable
from typing import Any

log = logging.getLogger(__name__)


def _report(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        log.critical("background task %s died", task.get_name(), exc_info=exc)


def spawn(coro: Coroutine[Any, Any, Any], name: str) -> asyncio.Task:
    task = asyncio.create_task(coro, name=name)
    task.add_done_callback(_report)
    return task


async def cancel_all(tasks: Iterable[asyncio.Task]) -> None:
    tasks = list(tasks)
    for task in tasks:
        task.cancel()
    # return_exceptions: one failed task must not stop us from waiting for the others
    await asyncio.gather(*tasks, return_exceptions=True)


def dead(tasks: Iterable[asyncio.Task]) -> list[str]:
    """Names of tasks that ended with an exception. (A replay that reached its end is fine.)"""
    return [
        t.get_name() for t in tasks if t.done() and not t.cancelled() and t.exception() is not None
    ]
