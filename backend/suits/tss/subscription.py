"""Subscribe to DCU and UIA on the new protocol (UDP 14141) and keep the subscription alive.

* Subscribe is re-sent until an Ack arrives: UDP can drop it, and the TSS has no keepalive.
* Ack 1 means our IP is not assigned to a team. ``TssSource`` turns that into
  ``link.tss == "unassigned"``; here we keep re-sending slowly until someone assigns us.
* If telemetry stops for longer than ``resubscribe_after_s`` (TSS restarted), subscribe again.

This module fetches; it never interprets flags. Every inbound datagram goes to
``TssSource.feed`` (the same decoder replay uses).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable

from suits.tss import codec
from suits.tss.source import SUB_CHANNEL, TssSource
from suits.tss.transport import Tap, UdpEndpoint

log = logging.getLogger(__name__)

DEVICES = (codec.Device.DCU, codec.Device.UIA)


class Subscription:
    def __init__(
        self,
        source: TssSource,
        host: str,
        port: int = 14141,
        tap: Tap | None = None,
        retry_s: float = 0.5,
        unassigned_retry_s: float = 1.0,
        resubscribe_after_s: float = 3.0,
        timestamp: Callable[[], float] = time.time,
    ) -> None:
        self._source = source
        self._remote = (host, port)
        self._tap = tap
        self.retry_s = retry_s
        self.unassigned_retry_s = unassigned_retry_s
        self.resubscribe_after_s = resubscribe_after_s
        self._timestamp = timestamp
        self._endpoint: UdpEndpoint | None = None
        self._ack: asyncio.Queue[codec.AckResult] = asyncio.Queue()
        self._telemetry_seen = asyncio.Event()
        self.subscribes_sent = 0

    def _on_datagram(self, data: bytes) -> None:
        packet = self._source.feed(SUB_CHANNEL, data)
        if packet is None:
            return
        if packet.code == codec.Code.ACK:
            with contextlib.suppress(codec.CodecError):
                self._ack.put_nowait(codec.parse_ack(packet))
        elif packet.code == codec.Code.TELEMETRY:
            self._telemetry_seen.set()

    async def run(self) -> None:
        """Run until cancelled. Reopens the socket if the OS closes it."""
        while True:
            self._endpoint = await UdpEndpoint.open(
                SUB_CHANNEL, self._remote, self._on_datagram, self._tap
            )
            try:
                await self._serve(self._endpoint)
            finally:
                self._endpoint.close()

    async def _serve(self, endpoint: UdpEndpoint) -> None:
        while not endpoint.closed.is_set():
            for device in DEVICES:
                await self._subscribe(endpoint, device)
            await self._watch_telemetry(endpoint)

    async def _subscribe(self, endpoint: UdpEndpoint, device: codec.Device) -> None:
        """Send Subscribe until Ack 0. Returns early if the socket closes."""
        while not endpoint.closed.is_set():
            self._drain_acks()
            endpoint.send(codec.build_subscribe(int(self._timestamp()), device))
            self.subscribes_sent += 1
            try:
                result = await asyncio.wait_for(self._ack.get(), self.retry_s)
            except TimeoutError:
                continue  # dropped Subscribe or Ack, or no TSS: send again
            if result == codec.AckResult.OK:
                log.info("subscribed to %s", device.name)
                return
            if result == codec.AckResult.UNASSIGNED:
                log.warning("TSS says this IP is not assigned to a team (Ack 1)")
            else:
                log.error("TSS rejected Subscribe to %s (Ack %d)", device.name, result)
            await asyncio.sleep(self.unassigned_retry_s)

    async def _watch_telemetry(self, endpoint: UdpEndpoint) -> None:
        """Return when telemetry has been silent for resubscribe_after_s."""
        while not endpoint.closed.is_set():
            self._telemetry_seen.clear()
            try:
                await asyncio.wait_for(self._telemetry_seen.wait(), self.resubscribe_after_s)
            except TimeoutError:
                log.warning("no DCU/UIA telemetry for %.1f s: subscribing again",
                            self.resubscribe_after_s)
                return

    def _drain_acks(self) -> None:
        while not self._ack.empty():
            self._ack.get_nowait()
