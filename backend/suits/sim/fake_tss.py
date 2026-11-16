"""A fake TSS: a real localhost UDP server that speaks both TSS dialects.

The backend cannot tell it from NASA's server, so tests exercise the real codec, retries and
timeouts. Values come from ``state`` (shaped like the TSS's EVA.json); tests change it freely.

Behaviour copied from TSS2027 at the commit in suits/tss/VERSION:
* Port "sub" (14141 on the real TSS): Subscribe -> Ack, then a telemetry packet per subscribed
  device once a second to the address the Subscribe came from. Bad packets are dropped silently.
* Port "legacy" (14142 + team): GET 1-8 -> the bare JSON of one section; SET 2001-2004 and
  2009-2020 (12 bytes with a float32 value) -> 4-byte reply ``01 00 00 00`` (``00 ...`` if unknown).

Test controls: ``ack_result``, ``drop_subscribes``, ``silent``, ``bad_json``.
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from suits.tasks import cancel_all, spawn
from suits.tss import codec

log = logging.getLogger(__name__)


def default_state() -> dict[str, Any]:
    """A calm suit mid-EVA: everything nominal, switches on primary."""
    return {
        "telemetry": {
            "primary_battery_level": 86.0,
            "secondary_battery_level": 99.0,
            "oxy_pri_storage": 92.0,
            "oxy_sec_storage": 99.0,
            "oxy_pri_pressure": 2800.0,
            "oxy_sec_pressure": 2990.0,
            "suit_pressure_oxy": 4.0,
            "suit_pressure_co2": 0.02,
            "suit_pressure_other": 0.0,
            "suit_pressure_total": 4.02,
            "helmet_pressure_co2": 0.03,
            "fan_pri_rpm": 30000.0,
            "fan_sec_rpm": 30000.0,
            "scrubber_a_co2_storage": 12.0,
            "scrubber_b_co2_storage": 3.0,
            "temperature": 21.0,
            "coolant_storage": 100.0,
            "coolant_gas_pressure": 50.0,
            "coolant_liquid_pressure": 500.0,
            "heart_rate": 92.0,
            "oxy_consumption": 0.1,
            "co2_production": 0.1,
            "eva_elapsed_time": 600,
        },
        "status": {"started": True},
        "dcu": {
            "batt": {"lu": False, "ps": True},
            "oxy": True,
            "comm": True,
            "fan": True,
            "pump": False,
            "co2": True,
        },
        "error": {"fan_error": False, "oxy_error": False, "power_error": False,
                  "scrubber_error": False},
        "imu": {"posx": -5668.5, "posy": -10045.6, "heading": 125.5},
        "uia": {
            "eva1_power": False,
            "eva1_oxy": False,
            "eva1_water_supply": False,
            "eva1_water_waste": False,
            "oxy_vent": False,
            "depress": False,
        },
        "ssu": {},
        "spec": {"id": 0},
    }


LEGACY_SECTIONS = {1: "telemetry", 2: "status", 3: "dcu", 4: "error", 5: "imu", 6: "uia",
                   7: "ssu", 8: "spec"}

# legacy SET command -> path in state (docs/notes/tss-driving-the-sim.md)
LEGACY_SETS: dict[int, tuple[str, ...]] = {
    2001: ("uia", "eva1_power"),
    2002: ("uia", "eva1_oxy"),
    2003: ("uia", "eva1_water_supply"),
    2004: ("uia", "eva1_water_waste"),
    2009: ("uia", "oxy_vent"),
    2010: ("uia", "depress"),
    2011: ("dcu", "batt", "lu"),
    2012: ("dcu", "oxy"),
    2013: ("dcu", "batt", "ps"),
    2014: ("dcu", "fan"),
    2015: ("dcu", "pump"),
    2016: ("dcu", "co2"),
    2017: ("imu", "posx"),
    2018: ("imu", "posy"),
    2019: ("imu", "heading"),
    2020: ("spec", "id"),
}
_FLOAT_SETS = {2017, 2018, 2019}
_INT_SETS = {2020}


def _flag(value: Any) -> int:
    return 1 if value else 0


class _Server(asyncio.DatagramProtocol):
    def __init__(
        self,
        handle: Callable[[bytes, tuple[str, int]], None],
        on_error: Callable[[], None],
    ) -> None:
        self._handle = handle
        self._on_error = on_error
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        assert isinstance(transport, asyncio.DatagramTransport)
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            self._handle(data, addr)
        except Exception:
            log.exception("fake TSS failed on a datagram")

    def error_received(self, exc: Exception) -> None:
        # e.g. a push to a client socket that has closed. On Windows' Proactor loop the socket
        # would stop receiving, so the fake rebinds the same port.
        log.debug("fake TSS socket error: %s", exc)
        self._on_error()

    def send(self, data: bytes, addr: tuple[str, int]) -> None:
        if self.transport is not None and not self.transport.is_closing():
            self.transport.sendto(data, addr)

    def close(self) -> None:
        if self.transport is not None:
            self.transport.close()


class FakeTss:
    def __init__(
        self,
        host: str = "127.0.0.1",
        sub_port: int = 0,
        legacy_port: int = 0,
        push_interval_s: float = 1.0,
        legacy_service_s: float = 0.0,
        state: dict[str, Any] | None = None,
    ) -> None:
        """``legacy_service_s`` > 0 serves one legacy datagram per that many seconds, like the
        real TSS (about 1.2 s; docs/notes/tss-legacy-port-is-slow.md). 0 answers at once."""
        self.host = host
        self._ports = [sub_port, legacy_port]
        self.push_interval_s = push_interval_s
        self.legacy_service_s = legacy_service_s
        self.state = state if state is not None else default_state()
        # test controls
        self.ack_result = codec.AckResult.OK
        self.drop_subscribes = 0  # drop this many Subscribe packets before answering
        self.silent = False  # answer nothing and push nothing
        self.bad_json = False  # legacy GET replies are not JSON
        # observations
        self.subscribers: dict[int, tuple[str, int]] = {}
        self.subscribes_received = 0
        self.legacy_gets: list[int] = []
        self.legacy_max_queue = 0  # deepest legacy backlog seen (with legacy_service_s > 0)
        self._legacy_queue: deque[tuple[bytes, tuple[str, int]]] = deque()
        self._sub: _Server | None = None
        self._legacy: _Server | None = None
        self._tasks: list[asyncio.Task] = []

    # ---- lifecycle ----

    async def start(self) -> None:
        try:
            self._sub = await self._bind(0, self._on_sub)
            self._legacy = await self._bind(1, self._on_legacy_datagram)
        except BaseException:
            await self.stop()
            raise
        self._tasks = [spawn(self._push_loop(), "fake-tss-push")]
        if self.legacy_service_s > 0:
            self._tasks.append(spawn(self._legacy_worker(), "fake-tss-legacy"))

    async def _bind(self, which: int, handle: Callable[[bytes, tuple[str, int]], None]) -> _Server:
        loop = asyncio.get_running_loop()
        _, server = await loop.create_datagram_endpoint(
            lambda: _Server(handle, lambda: self._schedule_rebind(which)),
            local_addr=(self.host, self._ports[which]),
        )
        self._ports[which] = server.transport.get_extra_info("sockname")[1]  # keep the port
        return server

    def _schedule_rebind(self, which: int) -> None:
        self._tasks.append(spawn(self._rebind(which), f"fake-tss-rebind-{which}"))

    async def _rebind(self, which: int) -> None:
        old = self._sub if which == 0 else self._legacy
        if old is not None:
            old.close()
        await asyncio.sleep(0)  # let the close finish before binding the same port
        handle = self._on_sub if which == 0 else self._on_legacy_datagram
        new = await self._bind(which, handle)
        if which == 0:
            self._sub = new
        else:
            self._legacy = new

    async def stop(self) -> None:
        await cancel_all(self._tasks)
        self._tasks = []
        for server in (self._sub, self._legacy):
            if server is not None:
                server.close()

    async def __aenter__(self) -> FakeTss:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    @property
    def sub_port(self) -> int:
        return self._bound_port(self._sub)

    @property
    def legacy_port(self) -> int:
        return self._bound_port(self._legacy)

    @staticmethod
    def _bound_port(server: _Server | None) -> int:
        if server is None or server.transport is None:
            raise RuntimeError("fake TSS is not running")
        return server.transport.get_extra_info("sockname")[1]

    # ---- new protocol ----

    def _on_sub(self, data: bytes, addr: tuple[str, int]) -> None:
        if self.silent:
            return
        try:
            packet = codec.decode(data)
        except codec.CodecError:
            return  # the real TSS drops bad packets without a reply
        now = int(time.time())
        if packet.code == codec.Code.SUBSCRIBE:
            self.subscribes_received += 1
            if self.drop_subscribes > 0:
                self.drop_subscribes -= 1
                return
            try:
                device = codec.parse_subscribe(packet)
            except codec.CodecError:
                self._reply(codec.build_ack(now, codec.AckResult.REJECTED), addr)
                return
            if device not in (codec.Device.DCU, codec.Device.UIA, codec.Device.SPM,
                              codec.Device.SSU, codec.Device.CTS, codec.Device.XRF):
                self._reply(codec.build_ack(now, codec.AckResult.REJECTED), addr)
                return
            if self.ack_result == codec.AckResult.OK:
                self.subscribers[device] = addr
            self._reply(codec.build_ack(now, self.ack_result), addr)
        elif packet.code == codec.Code.UNSUBSCRIBE:
            for device in (codec.Device.SPM, codec.Device.SSU, codec.Device.CTS, codec.Device.XRF):
                self.subscribers.pop(device, None)
            self._reply(codec.build_ack(now, codec.AckResult.OK), addr)

    def _reply(self, data: bytes, addr: tuple[str, int]) -> None:
        if self._sub is not None:
            self._sub.send(data, addr)

    async def _push_loop(self) -> None:
        while True:
            await asyncio.sleep(self.push_interval_s)
            if not self.silent:
                try:
                    self.push_now()
                except Exception:  # e.g. a test removed a key from state: keep pushing
                    log.exception("fake TSS push failed")

    def send_raw(self, data: bytes, device: int = codec.Device.DCU) -> None:
        """Send any bytes to the subscriber of ``device`` (tests: corrupt packets)."""
        addr = self.subscribers.get(device)
        if addr is None:
            raise RuntimeError(f"nobody is subscribed to device {device}")
        self._reply(data, addr)

    def push_now(self) -> None:
        """Send one telemetry packet to every subscriber (the 1 Hz push, on demand)."""
        now = int(time.time())
        for device, addr in list(self.subscribers.items()):
            payload = self._payload(device)
            if payload is not None:
                self._reply(codec.build_telemetry(now, codec.Device(device), payload), addr)

    def _payload(self, device: int) -> bytes | None:
        if device == codec.Device.DCU:
            dcu = self.state["dcu"]
            return codec.encode_dcu(codec.DcuFlags(
                batt=_flag(dcu["batt"]["lu"]), oxy=_flag(dcu["oxy"]), comm=_flag(dcu["comm"]),
                fan=_flag(dcu["fan"]), pump=_flag(dcu["pump"]), co2=_flag(dcu["co2"]),
            ))
        if device == codec.Device.UIA:
            uia = self.state["uia"]
            return codec.encode_uia(codec.UiaFlags(
                eva_power=_flag(uia["eva1_power"]),
                water_supply=_flag(uia["eva1_water_supply"]),
                water_waste=_flag(uia["eva1_water_waste"]),
                o2_supply=_flag(uia["eva1_oxy"]),
                o2_vent=_flag(uia["oxy_vent"]),
                depress=_flag(uia["depress"]),
            ))
        return None  # SPM/SSU/CTS/XRF: subscribable but not simulated yet

    # ---- legacy ports ----

    def _on_legacy_datagram(self, data: bytes, addr: tuple[str, int]) -> None:
        if self.legacy_service_s <= 0:
            self._on_legacy(data, addr)
            return
        self._legacy_queue.append((data, addr))
        self.legacy_max_queue = max(self.legacy_max_queue, len(self._legacy_queue))

    async def _legacy_worker(self) -> None:
        """Serve one queued legacy datagram per legacy_service_s, like the real TSS loop."""
        while True:
            await asyncio.sleep(self.legacy_service_s)
            if self._legacy_queue:
                data, addr = self._legacy_queue.popleft()
                try:
                    self._on_legacy(data, addr)
                except Exception:
                    log.exception("fake TSS failed on a legacy datagram")

    def _on_legacy(self, data: bytes, addr: tuple[str, int]) -> None:
        if self.silent:
            return
        try:
            request = codec.parse_legacy_request(data)
        except codec.CodecError:
            return
        if request.command < 1000:
            self.legacy_gets.append(request.command)
            self._legacy_reply(self._get(request.command), addr)
        elif request.command < 3000:
            ok = request.value is not None and self._set(request.command, request.value)
            self._legacy_reply(codec.LEGACY_SET_OK if ok else b"\x00\x00\x00\x00", addr)

    def _get(self, command: int) -> bytes:
        section = LEGACY_SECTIONS.get(command)
        if section is None:
            return b""  # the real TSS sends an empty datagram for an unknown GET
        if self.bad_json:
            return b'{"primary_battery_level": 86.0, "oxy_pri_sto'
        return json.dumps(self.state.get(section, {}), indent="\t").encode("utf-8")

    def _set(self, command: int, value: float) -> bool:
        path = LEGACY_SETS.get(command)
        if path is None:
            return False
        if command in _FLOAT_SETS:
            new: Any = float(value)
        elif command in _INT_SETS:
            new = int(value)
        else:
            new = value != 0.0
        target = self.state
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = new
        return True

    def _legacy_reply(self, data: bytes, addr: tuple[str, int]) -> None:
        if self._legacy is not None:
            self._legacy.send(data, addr)

    def snapshot_state(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)
