"""Poll the legacy per-team port (14142 + team) for telemetry, status and faults once a second.

A legacy GET reply is the bare JSON of one section, with no name in it, so each command gets
its own socket: the reply on that socket belongs to that command. No team assignment is needed
on these ports (docs/notes/tss-team-must-be-assigned.md).

This module fetches; it never interprets. Replies go to ``TssSource.feed``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from suits.tss import codec
from suits.tss.source import LEGACY_COMMANDS, TssSource, legacy_channel
from suits.tss.transport import Tap, UdpEndpoint

log = logging.getLogger(__name__)


class LegacyPoller:
    def __init__(
        self,
        source: TssSource,
        host: str,
        port: int,
        tap: Tap | None = None,
        interval_s: float = 1.0,
        timestamp: Callable[[], float] = time.time,
    ) -> None:
        self._source = source
        self._remote = (host, port)
        self._tap = tap
        self.interval_s = interval_s
        self._timestamp = timestamp
        self._endpoints: dict[codec.LegacyCommand, UdpEndpoint] = {}

    async def run(self) -> None:
        """Run until cancelled. Reopens any socket the OS closes."""
        try:
            while True:
                await self._open_missing()
                ts = int(self._timestamp())
                for command, endpoint in self._endpoints.items():
                    endpoint.send(codec.build_legacy_get(ts, command))
                await asyncio.sleep(self.interval_s)
        finally:
            for endpoint in self._endpoints.values():
                endpoint.close()

    async def _open_missing(self) -> None:
        for command in LEGACY_COMMANDS:
            endpoint = self._endpoints.get(command)
            if endpoint is not None and not endpoint.closed.is_set():
                continue
            channel = legacy_channel(command)
            self._endpoints[command] = await UdpEndpoint.open(
                channel, self._remote, self._handler(channel), self._tap
            )

    def _handler(self, channel: str) -> Callable[[bytes], None]:
        def handle(data: bytes) -> None:
            self._source.feed(channel, data)

        return handle
