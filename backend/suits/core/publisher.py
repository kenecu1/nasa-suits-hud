"""When to send State: a 1 s heartbeat, and soon after anything changes.

Changes are gathered for ``coalesce_s`` (about 100 ms) and sent as one message (decision B in
docs/briefs/M1.md): DCU, UIA and three legacy replies land at different moments in each
second, and one calm update is better than five. Every message is the full state, so a
client that joins late or reconnects needs no catch-up.

Subscribers get an asyncio.Queue. A slow subscriber only ever misses old states, never the
newest one. No sockets here; app.py moves queue items onto WebSockets.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from suits.contract import State, TssSnapshot
from suits.core.store import Store, content_key

log = logging.getLogger(__name__)

QUEUE_SIZE = 4


class Publisher:
    def __init__(
        self,
        snapshot: Callable[[], TssSnapshot],
        store: Store,
        coalesce_s: float = 0.1,
        heartbeat_s: float = 1.0,
    ) -> None:
        self._snapshot = snapshot
        self._store = store
        self.coalesce_s = coalesce_s
        self.heartbeat_s = heartbeat_s
        self._changed = asyncio.Event()
        self._queues: set[asyncio.Queue[State]] = set()
        self._last_key: str | None = None
        self.latest: State | None = None

    # ---- inputs ----

    def notify_change(self) -> None:
        """Call from the event loop thread whenever the source has new data."""
        self._changed.set()

    def subscribe(self) -> asyncio.Queue[State]:
        queue: asyncio.Queue[State] = asyncio.Queue(maxsize=QUEUE_SIZE)
        if self.latest is not None:
            queue.put_nowait(self.latest)
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[State]) -> None:
        self._queues.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)

    # ---- loop ----

    async def run(self) -> None:
        next_beat = time.monotonic()
        while True:
            timeout = max(0.0, next_beat - time.monotonic())
            try:
                await asyncio.wait_for(self._changed.wait(), timeout)
                await asyncio.sleep(self.coalesce_s)  # let the rest of this burst arrive
                self._changed.clear()
            except TimeoutError:
                pass
            beat_due = time.monotonic() >= next_beat
            self.publish(force=beat_due)
            if beat_due:
                next_beat += self.heartbeat_s
                if next_beat < time.monotonic():  # fell behind (e.g. a debugger pause)
                    next_beat = time.monotonic() + self.heartbeat_s

    def publish(self, force: bool = False) -> State | None:
        """Build State; send it if forced (heartbeat) or if its content changed."""
        try:
            state = self._store.preview(self._snapshot())
        except Exception:
            # Never let one bad snapshot stop the heartbeat; the log says what happened.
            log.exception("could not build state")
            return None
        key = content_key(state)
        if not force and key == self._last_key:
            return None
        self._store.commit(state)
        self._last_key = key
        self.latest = state
        for queue in self._queues:
            _put_latest(queue, state)
        return state


def _put_latest(queue: asyncio.Queue[State], state: State) -> None:
    while True:
        try:
            queue.put_nowait(state)
            return
        except asyncio.QueueFull:
            queue.get_nowait()  # drop the oldest; full state makes it redundant
