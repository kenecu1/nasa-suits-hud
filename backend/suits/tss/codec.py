"""Build and parse TSS packets. No networking, no state.

Two dialects (see docs/notes/tss-packet-format.md and tss-suit-telemetry-is-legacy-only.md):

* New protocol, UDP 14141: 10-byte big-endian header (uint32 timestamp, uint16 total length,
  uint16 device id, uint16 code), data, 1-byte XOR checksum of every byte before it.
* Legacy per-team ports (14142 + team): request ``uint32 timestamp, uint32 command`` (GET) or
  ``... , float32 value`` (SET), all big-endian. A GET reply is the bare JSON of one section.

Payload layouts are from src/data.c at the commit in VERSION, not from NASA's README
(see docs/notes/tss-readme-payload-sizes-wrong.md). Decoders accept a payload longer than
expected and reject a shorter one. They return raw flags; names live in mapping.py.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from enum import IntEnum

HEADER = struct.Struct(">IHHH")
HEADER_SIZE = HEADER.size  # 10
MIN_PACKET_SIZE = HEADER_SIZE + 1  # header + checksum, no data


class Device(IntEnum):
    DCU = 1
    UIA = 2
    SPM = 3
    SSU = 4
    CTS = 5
    XRF = 6
    TEAM = 15  # our own device id; every packet we send uses it


class Code(IntEnum):
    SUBSCRIBE = 1
    UNSUBSCRIBE = 2
    TELEMETRY = 3
    ACK = 4


class AckResult(IntEnum):
    OK = 0
    UNASSIGNED = 1  # our IP is not assigned to a team in the TSS web UI
    REJECTED = 2  # bad device id or length


# ---- errors ----


class CodecError(ValueError):
    """Base class: a datagram could not be decoded. The receive loop catches this."""


class PacketTooShort(CodecError):
    pass


class LengthMismatch(CodecError):
    pass


class BadChecksum(CodecError):
    pass


class UnknownCode(CodecError):
    pass


class PayloadTooShort(CodecError):
    pass


class BadJson(CodecError):
    pass


# ---- new protocol framing ----


@dataclass(frozen=True)
class Packet:
    timestamp: int
    device: int  # a Device value, kept as int so unknown devices still decode
    code: Code
    data: bytes


def checksum(data: bytes) -> int:
    result = 0
    for byte in data:
        result ^= byte
    return result


def encode(timestamp: int, device: int, code: Code, data: bytes = b"") -> bytes:
    length = HEADER_SIZE + len(data) + 1
    body = HEADER.pack(timestamp & 0xFFFFFFFF, length, device, code) + data
    return body + bytes([checksum(body)])


def decode(datagram: bytes) -> Packet:
    """Check size, length field and checksum, then split into a Packet. Raises CodecError."""
    if len(datagram) < MIN_PACKET_SIZE:
        raise PacketTooShort(f"{len(datagram)} bytes, need at least {MIN_PACKET_SIZE}")
    timestamp, length, device, code = HEADER.unpack_from(datagram)
    if length != len(datagram):
        raise LengthMismatch(f"length field says {length}, datagram has {len(datagram)} bytes")
    expected = checksum(datagram[:-1])
    if datagram[-1] != expected:
        raise BadChecksum(f"checksum {datagram[-1]:#04x}, expected {expected:#04x}")
    try:
        code = Code(code)
    except ValueError as exc:
        raise UnknownCode(f"message code {code}") from exc
    return Packet(timestamp, device, code, bytes(datagram[HEADER_SIZE:-1]))


def build_subscribe(timestamp: int, device: Device) -> bytes:
    return encode(timestamp, Device.TEAM, Code.SUBSCRIBE, struct.pack(">H", device))


def build_unsubscribe(timestamp: int) -> bytes:
    return encode(timestamp, Device.TEAM, Code.UNSUBSCRIBE)


def build_ack(timestamp: int, result: AckResult) -> bytes:
    return encode(timestamp, Device.TEAM, Code.ACK, bytes([result]))


def build_telemetry(timestamp: int, device: Device, payload: bytes) -> bytes:
    return encode(timestamp, device, Code.TELEMETRY, payload)


def parse_subscribe(packet: Packet) -> int:
    """The device id asked for in a Subscribe packet."""
    _require(packet.data, 2, "Subscribe")
    return struct.unpack_from(">H", packet.data)[0]


def parse_ack(packet: Packet) -> AckResult:
    _require(packet.data, 1, "Ack")
    try:
        return AckResult(packet.data[0])
    except ValueError as exc:
        raise CodecError(f"unknown Ack result {packet.data[0]}") from exc


# ---- payloads (raw flags; names are given in mapping.py) ----


@dataclass(frozen=True)
class DcuFlags:
    batt: int
    oxy: int
    comm: int
    fan: int
    pump: int
    co2: int


DCU_SIZE = 6


@dataclass(frozen=True)
class UiaFlags:
    eva_power: int
    water_supply: int
    water_waste: int
    o2_supply: int
    o2_vent: int
    depress: int


UIA_SIZE = 6  # the TSS sends 12 bytes; bytes 6-11 are uninitialised memory


@dataclass(frozen=True)
class SsuDrill:
    sensor: int
    state: int
    thermal: int
    depth_cm: float
    temp_c: float
    rpm: float


@dataclass(frozen=True)
class SsuData:
    power: int
    status: int
    mode: int
    sp: SsuDrill
    bb: SsuDrill


SSU_SIZE = 33
_SSU_DRILL = struct.Struct(">BBBfff")  # 15 bytes


def decode_dcu(payload: bytes) -> DcuFlags:
    _require(payload, DCU_SIZE, "DCU")
    return DcuFlags(*payload[:DCU_SIZE])


def encode_dcu(flags: DcuFlags) -> bytes:
    return bytes([flags.batt, flags.oxy, flags.comm, flags.fan, flags.pump, flags.co2])


def decode_uia(payload: bytes) -> UiaFlags:
    _require(payload, UIA_SIZE, "UIA")
    return UiaFlags(*payload[:UIA_SIZE])


def encode_uia(flags: UiaFlags, pad_to: int = 12) -> bytes:
    """As the TSS sends it: 6 flag bytes, padded with zeros to 12."""
    raw = bytes(
        [
            flags.eva_power,
            flags.water_supply,
            flags.water_waste,
            flags.o2_supply,
            flags.o2_vent,
            flags.depress,
        ]
    )
    return raw.ljust(pad_to, b"\x00")


def decode_ssu(payload: bytes) -> SsuData:
    _require(payload, SSU_SIZE, "SSU")
    sp = SsuDrill(*_SSU_DRILL.unpack_from(payload, 3))
    bb = SsuDrill(*_SSU_DRILL.unpack_from(payload, 18))
    return SsuData(payload[0], payload[1], payload[2], sp, bb)


def _require(payload: bytes, size: int, what: str) -> None:
    if len(payload) < size:
        raise PayloadTooShort(f"{what} payload is {len(payload)} bytes, need {size}")


# ---- legacy per-team ports ----

LEGACY_BASE_PORT = 14142
_LEGACY_GET = struct.Struct(">II")
_LEGACY_SET = struct.Struct(">IIf")
LEGACY_SET_OK = b"\x01\x00\x00\x00"  # the TSS replies with a native-endian uint32 1


class LegacyCommand(IntEnum):
    TELEMETRY = 1
    STATUS = 2
    DCU = 3
    ERROR = 4
    IMU = 5
    UIA = 6
    SSU = 7
    SPEC = 8


def legacy_port(team: int) -> int:
    if not 0 <= team <= 9:
        raise ValueError(f"team must be 0-9, got {team}")
    return LEGACY_BASE_PORT + team


def build_legacy_get(timestamp: int, command: int) -> bytes:
    return _LEGACY_GET.pack(timestamp & 0xFFFFFFFF, command)


def build_legacy_set(timestamp: int, command: int, value: float) -> bytes:
    return _LEGACY_SET.pack(timestamp & 0xFFFFFFFF, command, value)


@dataclass(frozen=True)
class LegacyRequest:
    timestamp: int
    command: int
    value: float | None  # None for a GET


def parse_legacy_request(datagram: bytes) -> LegacyRequest:
    if len(datagram) >= _LEGACY_SET.size:
        return LegacyRequest(*_LEGACY_SET.unpack_from(datagram))
    if len(datagram) >= _LEGACY_GET.size:
        timestamp, command = _LEGACY_GET.unpack_from(datagram)
        return LegacyRequest(timestamp, command, None)
    raise PacketTooShort(f"legacy request is {len(datagram)} bytes, need 8")


def parse_legacy_reply(datagram: bytes) -> dict:
    """A GET reply: the JSON object of one EVA.json section. Raises BadJson."""
    try:
        value = json.loads(datagram.rstrip(b"\x00").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BadJson(f"legacy reply is not JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise BadJson(f"legacy reply is {type(value).__name__}, expected an object")
    return value
