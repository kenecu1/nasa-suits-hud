"""The TSS adapter's state: every inbound datagram goes through ``TssSource.feed``.

Live transports (subscription.py, legacy.py) and the replayer (recorder.py) call the same
``feed``, so a recording tests the real decoder. ``snapshot()`` turns what has arrived into a
``TssSnapshot``, including the one link status (decision A in docs/briefs/M1.md), how many
times each section has arrived, and which expected telemetry names are missing (decision A
in docs/briefs/M2.md: the link is ``bad_data`` while any are missing).

Channels name where a datagram came from:
* ``"sub"``: the new protocol socket (port 14141)
* ``"legacy/<command>"``: the legacy socket that sent GET <command> (replies carry no section name)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from suits.contract import (
    LINK_SILENT_AFTER_S,
    SECTIONS,
    STALE_AFTER_S,
    LinkStatus,
    Section,
    TssSnapshot,
)
from suits.tss import codec, mapping

log = logging.getLogger(__name__)

SUB_CHANNEL = "sub"
LEGACY_COMMANDS: dict[codec.LegacyCommand, Section] = {
    codec.LegacyCommand.TELEMETRY: "telemetry",
    codec.LegacyCommand.STATUS: "status",
    codec.LegacyCommand.ERROR: "faults",
}


def legacy_channel(command: int) -> str:
    return f"legacy/{int(command)}"


_CHANNEL_SECTION: dict[str, Section] = {legacy_channel(c): s for c, s in LEGACY_COMMANDS.items()}


@dataclass
class _Received:
    value: Any
    at: float  # clock() time


@dataclass
class _ChannelHealth:
    last_ok: bool
    at: float


class TssSource:
    """Holds the newest value of each section and when it arrived. Not thread-safe; one loop."""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._clock = clock
        self._wall = wall
        self.on_change = on_change
        self._sections: dict[Section, _Received] = {}
        self._arrivals: dict[Section, int] = {}  # every arrival counts, changed or not
        self._missing: tuple[str, ...] = ()  # expected names absent from the newest telemetry
        self._channels: dict[str, _ChannelHealth] = {}
        # Set by Ack 1, cleared only by Ack 0: a lost Ack must not make the link flicker.
        self._unassigned = False
        self._last_valid_at: float | None = None  # any datagram that decoded, Acks included
        self.decode_errors = 0
        self.last_error: str | None = None

    # ---- inbound ----

    def feed(self, channel: str, datagram: bytes) -> codec.Packet | None:
        """Decode one inbound datagram and update state. Never raises on bad data.

        Returns the decoded packet for the ``sub`` channel (so the subscription can see Acks),
        otherwise None.
        """
        try:
            if channel == SUB_CHANNEL:
                packet = codec.decode(datagram)
                self._on_packet(packet)
                result = packet
            elif channel in _CHANNEL_SECTION:
                self._on_legacy(_CHANNEL_SECTION[channel], codec.parse_legacy_reply(datagram))
                result = None
            else:
                raise codec.CodecError(f"unknown channel {channel!r}")
        except codec.CodecError as exc:
            self._bad(channel, exc)
            log.warning("bad TSS datagram on %s: %s (%d bytes)", channel, exc, len(datagram))
            return None
        except Exception as exc:  # e.g. RecursionError on absurd JSON: still bad data, not a crash
            self._bad(channel, exc)
            log.exception("unexpected error decoding a TSS datagram on %s", channel)
            return None
        self._mark(channel, ok=True)
        self._last_valid_at = self._clock()
        return result

    def _bad(self, channel: str, exc: Exception) -> None:
        self._mark(channel, ok=False)
        self.decode_errors += 1
        self.last_error = f"{channel}: {exc}"
        self._changed()

    def _on_packet(self, packet: codec.Packet) -> None:
        if packet.code == codec.Code.ACK:
            result = codec.parse_ack(packet)
            was = self._unassigned
            if result == codec.AckResult.UNASSIGNED:
                self._unassigned = True
            elif result == codec.AckResult.OK:
                self._unassigned = False
            if was != self._unassigned:
                self._changed()
            return
        if packet.code != codec.Code.TELEMETRY:
            return  # the server never sends Subscribe/Unsubscribe to us; ignore
        if packet.device == codec.Device.DCU:
            self._store("dcu", mapping.dcu_positions(codec.decode_dcu(packet.data)))
        elif packet.device == codec.Device.UIA:
            self._store("uia", mapping.uia_positions(codec.decode_uia(packet.data)))
        else:
            return  # SPM/SSU/CTS/XRF are decoded by codec but not used before M7
        # The TSS pushes DCU/UIA only to an assigned team, so a valid push proves assignment
        # even if a stray late Ack 1 arrived after the last Ack 0.
        if self._unassigned:
            self._unassigned = False
            self._changed()

    def _on_legacy(self, section: Section, body: dict[str, Any]) -> None:
        if section == "telemetry":
            values = mapping.telemetry_values(body)
            missing = mapping.missing_telemetry(values)
            if missing != self._missing:
                if missing:
                    log.warning("TSS telemetry is missing expected names: %s", ", ".join(missing))
                else:
                    log.info("TSS telemetry has every expected name again")
                self._missing = missing
                self._changed()
            self._store(section, values)
        elif section == "status":
            self._store(section, mapping.eva_started(body))
        elif section == "faults":
            self._store(section, mapping.suit_faults(body))

    def _store(self, section: Section, value: Any) -> None:
        previous = self._sections.get(section)
        self._sections[section] = _Received(value, self._clock())
        self._arrivals[section] = self._arrivals.get(section, 0) + 1
        if previous is None or previous.value != value:
            self._changed()

    def _mark(self, channel: str, ok: bool) -> None:
        previous = self._channels.get(channel)
        self._channels[channel] = _ChannelHealth(ok, self._clock())
        if previous is not None and previous.last_ok != ok:
            self._changed()

    def _changed(self) -> None:
        if self.on_change is not None:
            self.on_change()

    # ---- outbound ----

    def snapshot(self) -> TssSnapshot:
        now = self._clock()
        ages: dict[Section, float] = {
            s: round(now - r.at, 3) for s, r in self._sections.items() if s in SECTIONS
        }
        return TssSnapshot(
            t=self._wall(),
            link=self._link(now, ages),
            ages=ages,
            arrivals=dict(self._arrivals),
            missing=self._missing,
            telemetry=self._value("telemetry", dict),
            elapsed_s=mapping.elapsed_seconds(self._value("telemetry", dict)),
            started=self._value("status", None),
            faults=self._value("faults", None),
            dcu=self._value("dcu", None),
            uia=self._value("uia", None),
        )

    def _value(self, section: Section, default_factory: Callable[[], Any] | None) -> Any:
        received = self._sections.get(section)
        if received is not None:
            return received.value
        return default_factory() if default_factory else None

    def _link(self, now: float, ages: dict[Section, float]) -> LinkStatus:
        """Worst first: unassigned, bad_data, unreachable, stale, ok (decision A).

        bad_data: the newest datagram on some path could not be decoded, or (after the
        unreachable check) the current telemetry lacks expected names.
        """

        def recent(at: float | None) -> bool:
            return at is not None and now - at <= LINK_SILENT_AFTER_S

        # unassigned holds until Ack 0, but only while the TSS is heard at all
        if self._unassigned and recent(self._last_valid_at):
            return LinkStatus.UNASSIGNED
        if any(not h.last_ok and recent(h.at) for h in self._channels.values()):
            return LinkStatus.BAD_DATA
        if not recent(self._last_valid_at):
            return LinkStatus.UNREACHABLE
        # Current telemetry lacks expected names: what did arrive is used, but the link must
        # not look healthy (decision A in docs/briefs/M2.md). A silent TSS is unreachable first.
        telemetry_age = ages.get("telemetry")
        if (
            self._missing
            and telemetry_age is not None
            and telemetry_age <= STALE_AFTER_S["telemetry"]
        ):
            return LinkStatus.BAD_DATA
        if any(s not in ages or ages[s] > STALE_AFTER_S[s] for s in SECTIONS):
            return LinkStatus.STALE
        return LinkStatus.OK
