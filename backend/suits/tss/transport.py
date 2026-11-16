"""A small asyncio UDP endpoint that survives errors. Shared by subscription.py and legacy.py.

On Windows an ICMP "port unreachable" (TSS not running yet) surfaces as an error on the
socket, and some event loops close the transport afterwards. ``UdpEndpoint`` reports errors,
never raises them into the receive path, and lets the owner reopen the socket.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

log = logging.getLogger(__name__)

Tap = Callable[[str, str, bytes], None]  # (direction "in"|"out", channel, datagram)


class UdpEndpoint(asyncio.DatagramProtocol):
    def __init__(self, channel: str, on_datagram: Callable[[bytes], None], tap: Tap | None):
        self.channel = channel
        self._on_datagram = on_datagram
        self._tap = tap
        self.transport: asyncio.DatagramTransport | None = None
        self.closed = asyncio.Event()
        self.errors = 0

    @classmethod
    async def open(
        cls,
        channel: str,
        remote: tuple[str, int],
        on_datagram: Callable[[bytes], None],
        tap: Tap | None = None,
    ) -> UdpEndpoint:
        loop = asyncio.get_running_loop()
        endpoint = cls(channel, on_datagram, tap)
        await loop.create_datagram_endpoint(lambda: endpoint, remote_addr=remote)
        return endpoint

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        assert isinstance(transport, asyncio.DatagramTransport)
        self.transport = transport

    def connection_lost(self, exc: Exception | None) -> None:
        if exc is not None:
            log.warning("%s socket closed: %s", self.channel, exc)
        self.transport = None
        self.closed.set()

    def error_received(self, exc: Exception) -> None:
        # Port unreachable and similar: the TSS is not there (yet). Silence is detected elsewhere.
        self.errors += 1
        log.debug("%s socket error: %s", self.channel, exc)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if self._tap is not None:
            self._tap("in", self.channel, data)
        try:
            self._on_datagram(data)
        except Exception:  # the receive loop must keep running whatever a handler does
            log.exception("handler failed for a datagram on %s", self.channel)

    def send(self, data: bytes) -> bool:
        if self.transport is None or self.transport.is_closing():
            return False
        if self._tap is not None:
            self._tap("out", self.channel, data)
        self.transport.sendto(data)
        return True

    def close(self) -> None:
        if self.transport is not None:
            self.transport.close()
