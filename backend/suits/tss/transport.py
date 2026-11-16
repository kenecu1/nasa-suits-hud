"""A small asyncio UDP endpoint that survives errors. Shared by subscription.py and legacy.py.

On Windows an ICMP "port unreachable" (TSS not running yet, or restarted) reaches the socket as
an error. With the Proactor event loop (uvicorn's default on Windows) the socket then stops
receiving for good while still looking open. So on any socket error we close the endpoint and
the owner opens a new one after a short pause. A failing recorder tap never stops a send or a
receive.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Literal

log = logging.getLogger(__name__)

Direction = Literal["in", "out"]
Tap = Callable[[Direction, str, bytes], None]  # (direction, channel, datagram)


class UdpEndpoint(asyncio.DatagramProtocol):
    def __init__(self, channel: str, on_datagram: Callable[[bytes], None], tap: Tap | None):
        self.channel = channel
        self._on_datagram = on_datagram
        self._tap = tap
        self.transport: asyncio.DatagramTransport | None = None
        self.closed = asyncio.Event()
        self.last_error: Exception | None = None

    @classmethod
    async def open(
        cls,
        channel: str,
        remote: tuple[str, int],
        on_datagram: Callable[[bytes], None],
        tap: Tap | None = None,
    ) -> UdpEndpoint:
        """Raises OSError if the socket cannot be created (bad host, no network)."""
        loop = asyncio.get_running_loop()
        endpoint = cls(channel, on_datagram, tap)
        await loop.create_datagram_endpoint(lambda: endpoint, remote_addr=remote)
        return endpoint

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        assert isinstance(transport, asyncio.DatagramTransport)
        self.transport = transport

    def connection_lost(self, exc: Exception | None) -> None:
        self.transport = None
        self.closed.set()

    def error_received(self, exc: Exception) -> None:
        # Usually "port unreachable": nobody listens there (yet). Close, so the owner reopens.
        self.last_error = exc
        log.info("%s socket error (%s): reopening", self.channel, exc)
        self.close()

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._record("in", data)
        try:
            self._on_datagram(data)
        except Exception:  # the receive loop must keep running whatever a handler does
            log.exception("handler failed for a datagram on %s", self.channel)

    def send(self, data: bytes) -> bool:
        if self.transport is None or self.transport.is_closing():
            return False
        self._record("out", data)
        self.transport.sendto(data)
        return True

    def _record(self, direction: Direction, data: bytes) -> None:
        if self._tap is None:
            return
        try:
            self._tap(direction, self.channel, data)
        except Exception:
            log.exception("recording failed on %s; recording stops, the link continues",
                          self.channel)
            self._tap = None

    def close(self) -> None:
        if self.transport is not None:
            self.transport.close()
        else:
            self.closed.set()
