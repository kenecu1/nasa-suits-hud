"""Poll the legacy per-team port (14142 + team) for telemetry, status and faults.

The real TSS answers about one request per team port every 1.2 s: its main loop handles one
datagram per port per pass (docs/notes/tss-legacy-port-is-slow.md). Sending faster builds a
queue on the TSS, and replies then arrive later and later while looking fresh. So exactly one
request is in flight at a time: the next one goes when the reply arrives (or after
``reply_timeout_s``), never sooner than ``min_gap_s`` after the last. Telemetry gets most
turns; status and faults change rarely.

A GET reply is the bare JSON of one section with no name in it, so each command has its own
socket: a reply on that socket belongs to that command. No team assignment is needed on these
ports (docs/notes/tss-team-must-be-assigned.md).

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

T, S, E = codec.LegacyCommand.TELEMETRY, codec.LegacyCommand.STATUS, codec.LegacyCommand.ERROR
SCHEDULE: tuple[codec.LegacyCommand, ...] = (T, T, S, T, T, E)


class LegacyPoller:
    def __init__(
        self,
        source: TssSource,
        host: str,
        port: int,
        tap: Tap | None = None,
        min_gap_s: float = 0.25,
        reply_timeout_s: float = 2.0,
        reopen_after_s: float = 1.0,
        timestamp: Callable[[], float] = time.time,
    ) -> None:
        self._source = source
        self._remote = (host, port)
        self._tap = tap
        self.min_gap_s = min_gap_s
        self.reply_timeout_s = reply_timeout_s
        self.reopen_after_s = reopen_after_s
        self._timestamp = timestamp
        self._endpoints: dict[codec.LegacyCommand, UdpEndpoint] = {}
        self._waiting_for: codec.LegacyCommand | None = None
        self._replied = asyncio.Event()
        self.timeouts = 0

    async def run(self) -> None:
        """Run until cancelled. Reopens sockets that close; never stops on a socket error."""
        turn = 0
        try:
            while True:
                try:
                    await self._open_missing()
                except OSError as exc:
                    log.warning("legacy socket to %s:%d failed: %s", *self._remote, exc)
                    await asyncio.sleep(self.reopen_after_s)
                    continue
                command = SCHEDULE[turn % len(SCHEDULE)]
                turn += 1
                await self._request(command)
        finally:
            for endpoint in self._endpoints.values():
                endpoint.close()

    async def _request(self, command: codec.LegacyCommand) -> None:
        started = time.monotonic()
        self._waiting_for = command
        self._replied.clear()
        if self._endpoints[command].send(codec.build_legacy_get(int(self._timestamp()), command)):
            try:
                await asyncio.wait_for(self._replied.wait(), self.reply_timeout_s)
            except TimeoutError:
                self.timeouts += 1
        self._waiting_for = None
        await asyncio.sleep(max(0.0, self.min_gap_s - (time.monotonic() - started)))

    async def _open_missing(self) -> None:
        for command in LEGACY_COMMANDS:
            endpoint = self._endpoints.get(command)
            if endpoint is not None and not endpoint.closed.is_set():
                continue
            if endpoint is not None:
                await asyncio.sleep(self.reopen_after_s)  # a closed socket: do not spin
            channel = legacy_channel(command)
            self._endpoints[command] = await UdpEndpoint.open(
                channel, self._remote, self._handler(command, channel), self._tap
            )

    def _handler(self, command: codec.LegacyCommand, channel: str) -> Callable[[bytes], None]:
        def handle(data: bytes) -> None:
            self._source.feed(channel, data)
            if command == self._waiting_for:
                self._replied.set()

        return handle
