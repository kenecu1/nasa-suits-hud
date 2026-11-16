"""Subscribe to DCU and UIA on the new protocol (UDP 14141) and keep the subscriptions alive.

* Subscribe is re-sent until an Ack arrives: UDP can drop it, and the TSS has no keepalive.
* Ack 1 means our IP is not assigned to a team. ``TssSource`` turns that into
  ``link.tss == "unassigned"``; here we keep re-sending slowly until someone assigns us.
* A device whose telemetry stops for ``resubscribe_after_s`` (TSS restarted, or it forgot one
  subscription) is subscribed again, each device on its own.
* A socket error closes the socket (see transport.py); a new one is opened after a pause.

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
SILENT_AFTER = 3  # unanswered Subscribes in a row before a warning


class Subscription:
    def __init__(
        self,
        source: TssSource,
        host: str,
        port: int = 14141,
        tap: Tap | None = None,
        retry_s: float = 1.0,  # the real TSS takes up to about 1 s to answer
        unassigned_retry_s: float = 1.0,
        resubscribe_after_s: float = 3.0,
        reopen_after_s: float = 1.0,
        timestamp: Callable[[], float] = time.time,
    ) -> None:
        self._source = source
        self._remote = (host, port)
        self._tap = tap
        self.retry_s = retry_s
        self.unassigned_retry_s = unassigned_retry_s
        self.resubscribe_after_s = resubscribe_after_s
        self.reopen_after_s = reopen_after_s
        self._timestamp = timestamp
        self._ack: asyncio.Queue[codec.AckResult] = asyncio.Queue()
        self._last_seen: dict[int, float] = {}  # device -> monotonic time of last telemetry
        self._last_ack: codec.AckResult | None = None
        self.subscribes_sent = 0
        self._unanswered = 0  # Subscribes in a row with no Ack

    def _on_datagram(self, data: bytes) -> None:
        packet = self._source.feed(SUB_CHANNEL, data)
        if packet is None:
            return
        if packet.code == codec.Code.ACK:
            with contextlib.suppress(codec.CodecError):
                self._ack.put_nowait(codec.parse_ack(packet))
        elif packet.code == codec.Code.TELEMETRY:
            self._last_seen[packet.device] = time.monotonic()

    async def run(self) -> None:
        """Run until cancelled. Never stops on a socket error."""
        while True:
            try:
                endpoint = await UdpEndpoint.open(
                    SUB_CHANNEL, self._remote, self._on_datagram, self._tap
                )
            except OSError as exc:
                log.warning("subscription socket to %s:%d failed: %s", *self._remote, exc)
                await asyncio.sleep(self.reopen_after_s)
                continue
            try:
                await self._serve(endpoint)
            except Exception:  # never let one bug end the only subscription loop
                log.exception("subscription loop failed; reopening")
            finally:
                endpoint.close()
            await asyncio.sleep(self.reopen_after_s)  # the socket closed: pause, then reopen

    async def _serve(self, endpoint: UdpEndpoint) -> None:
        self._last_seen.clear()  # a new socket has no subscriptions yet
        while not endpoint.closed.is_set():
            now = time.monotonic()
            for device in DEVICES:
                seen = self._last_seen.get(device)
                if seen is None or now - seen > self.resubscribe_after_s:
                    if seen is not None:
                        log.warning("no %s telemetry for %.1f s: subscribing again",
                                    device.name, now - seen)
                    if await self._subscribe(endpoint, device):
                        # give the first push a full window before judging it missing
                        self._last_seen[device] = time.monotonic()
            await _wait_or_closed(endpoint, 0.5)

    async def _subscribe(self, endpoint: UdpEndpoint, device: codec.Device) -> bool:
        """Send Subscribe until Ack 0. False if the socket closed first.

        Acks carry no device id. Old Acks are cleared once, before the first send for this
        device, never before a resend: the real TSS can take a second to answer, and a late Ack
        for an earlier send of the same Subscribe is a valid answer.
        """
        self._drain_acks()
        while not endpoint.closed.is_set():
            if endpoint.send(codec.build_subscribe(int(self._timestamp()), device)):
                self.subscribes_sent += 1
            try:
                result = await asyncio.wait_for(self._ack.get(), self.retry_s)
            except TimeoutError:
                self._unanswered += 1
                if self._unanswered == SILENT_AFTER:
                    log.warning("no answer to Subscribe from the TSS at %s:%d after %d tries "
                                "(TSS down, or blocked by a firewall?)", *self._remote,
                                SILENT_AFTER)
                continue  # dropped Subscribe or Ack, or no TSS: send again
            if self._unanswered >= SILENT_AFTER:
                log.info("TSS at %s:%d is answering again", *self._remote)
            self._unanswered = 0
            self._log_ack(result, device)
            if result == codec.AckResult.OK:
                return True
            await _wait_or_closed(endpoint, self.unassigned_retry_s)
        return False

    def _log_ack(self, result: codec.AckResult, device: codec.Device) -> None:
        if result == self._last_ack and result != codec.AckResult.OK:
            return  # say "not assigned" once, not every second
        self._last_ack = result
        if result == codec.AckResult.OK:
            log.info("subscribed to %s", device.name)
        elif result == codec.AckResult.UNASSIGNED:
            log.warning("TSS says this IP is not assigned to a team (Ack 1): assign it in the "
                        "TSS web UI")
        else:
            log.error("TSS rejected Subscribe to %s (Ack %d)", device.name, result)

    def _drain_acks(self) -> None:
        while not self._ack.empty():
            self._ack.get_nowait()


async def _wait_or_closed(endpoint: UdpEndpoint, seconds: float) -> None:
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(endpoint.closed.wait(), seconds)
