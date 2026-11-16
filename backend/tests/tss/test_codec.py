"""Packet codec: captured packets from docs/notes/tss-packet-format.md, and the error cases."""

import pytest
from suits.tss import codec
from suits.tss.codec import Code, Device
from suits.tss.source import TssSource

SUBSCRIBE_DCU = bytes.fromhex("6af55d2c000d000f00010001ec")
ACK_OK = bytes.fromhex("6af55d33000c000f000400f6")
DCU_IDLE = bytes.fromhex("6af55d34001100010003000000000000e5")
UIA = bytes.fromhex("6af55d340017000200030000000000000000a0536a354c")
SSU_IDLE = bytes.fromhex(
    "6af55d34002c0004000300000000000000000000c1c800000000000000000000000000c1c8000000000000dd"
)


# ---- captured packets ----


def test_subscribe_to_dcu_decodes():
    packet = codec.decode(SUBSCRIBE_DCU)
    assert packet.timestamp == 0x6AF55D2C
    assert packet.device == Device.TEAM
    assert packet.code == Code.SUBSCRIBE
    assert codec.parse_subscribe(packet) == Device.DCU


def test_build_subscribe_matches_captured_bytes():
    assert codec.build_subscribe(0x6AF55D2C, Device.DCU).hex() == "6af55d2c000d000f00010001ec"


def test_ack_ok_decodes():
    packet = codec.decode(ACK_OK)
    assert packet.timestamp == 0x6AF55D33
    assert packet.code == Code.ACK
    assert codec.parse_ack(packet) == codec.AckResult.OK


def test_dcu_with_all_flags_zero_decodes():
    packet = codec.decode(DCU_IDLE)
    assert packet.device == Device.DCU
    assert packet.code == Code.TELEMETRY
    assert codec.decode_dcu(packet.data) == codec.DcuFlags(0, 0, 0, 0, 0, 0)


def test_uia_keeps_six_valid_bytes_and_ignores_garbage():
    packet = codec.decode(UIA)
    assert packet.device == Device.UIA
    assert len(packet.data) == 12
    assert packet.data[6:] != bytes(6)  # the capture really has garbage after the flags
    assert codec.decode_uia(packet.data) == codec.UiaFlags(0, 0, 0, 0, 0, 0)


def test_ssu_idle_has_both_drill_temps_at_minus_25():
    packet = codec.decode(SSU_IDLE)
    assert packet.device == Device.SSU
    ssu = codec.decode_ssu(packet.data)
    assert (ssu.power, ssu.status, ssu.mode) == (0, 0, 0)
    idle_drill = codec.SsuDrill(sensor=0, state=0, thermal=0, depth_cm=0.0, temp_c=-25.0, rpm=0.0)
    assert ssu.sp == idle_drill
    assert ssu.bb == idle_drill


def test_encode_then_decode_round_trips():
    datagram = codec.encode(0x6AF55D34, Device.DCU, Code.TELEMETRY, bytes([1, 0, 1, 0, 1, 0]))
    packet = codec.decode(datagram)
    assert (packet.timestamp, packet.device, packet.code) == (0x6AF55D34, Device.DCU, Code.TELEMETRY)
    assert codec.decode_dcu(packet.data) == codec.DcuFlags(1, 0, 1, 0, 1, 0)


# ---- bad packets ----

WRONG_CHECKSUM = DCU_IDLE[:-1] + b"\xe4"
LENGTH_TOO_BIG = DCU_IDLE + b"\x00"  # datagram is longer than its length field says
LENGTH_TOO_SMALL = DCU_IDLE[:-1]  # last byte lost in transit

BAD_PACKETS = [
    pytest.param(WRONG_CHECKSUM, codec.BadChecksum, id="wrong-checksum"),
    pytest.param(LENGTH_TOO_BIG, codec.LengthMismatch, id="datagram-longer-than-length-field"),
    pytest.param(LENGTH_TOO_SMALL, codec.LengthMismatch, id="datagram-shorter-than-length-field"),
    pytest.param(b"", codec.PacketTooShort, id="empty"),
    pytest.param(b"\x00", codec.PacketTooShort, id="one-byte"),
    pytest.param(DCU_IDLE[:10], codec.PacketTooShort, id="ten-bytes"),
]


@pytest.mark.parametrize(("datagram", "error"), BAD_PACKETS)
def test_bad_packet_raises_its_own_error(datagram, error):
    with pytest.raises(error) as raised:
        codec.decode(datagram)
    assert type(raised.value) is error
    assert isinstance(raised.value, codec.CodecError)


def test_eleven_bytes_is_the_smallest_packet_that_decodes():
    datagram = codec.encode(1, Device.DCU, Code.UNSUBSCRIBE)
    assert len(datagram) == 11
    assert codec.decode(datagram).data == b""


@pytest.mark.parametrize(("datagram", "_error"), BAD_PACKETS)
def test_receive_loop_survives_bad_datagrams(datagram, _error):
    source = TssSource()
    assert source.feed("sub", datagram) is None
    assert source.decode_errors == 1
    assert source.snapshot().dcu is None


def test_good_dcu_packet_is_decoded_after_bad_ones():
    source = TssSource()
    for params in BAD_PACKETS:
        assert source.feed("sub", params.values[0]) is None

    assert source.decode_errors == len(BAD_PACKETS)
    assert source.snapshot().dcu is None

    packet = source.feed("sub", DCU_IDLE)

    assert packet is not None
    assert packet.device == Device.DCU
    assert source.decode_errors == len(BAD_PACKETS)
    assert source.snapshot().dcu is not None


# ---- payload sizes ----


def test_uia_decodes_from_the_first_six_bytes_of_twelve():
    payload = bytes([1, 0, 1, 0, 1, 1]) + b"\xff" * 6
    assert codec.decode_uia(payload) == codec.UiaFlags(1, 0, 1, 0, 1, 1)


def test_uia_payload_of_five_bytes_is_rejected():
    with pytest.raises(codec.PayloadTooShort):
        codec.decode_uia(bytes(5))


def test_uia_payload_of_exactly_six_bytes_is_accepted():
    assert codec.decode_uia(bytes([0, 1, 0, 1, 0, 1])) == codec.UiaFlags(0, 1, 0, 1, 0, 1)


def test_dcu_payload_of_five_bytes_is_rejected():
    with pytest.raises(codec.PayloadTooShort):
        codec.decode_dcu(bytes(5))


def test_dcu_payload_longer_than_six_is_accepted():
    assert codec.decode_dcu(bytes([1, 1, 0, 0, 1, 0, 9, 9])) == codec.DcuFlags(1, 1, 0, 0, 1, 0)


def test_ssu_payload_shorter_than_33_is_rejected():
    with pytest.raises(codec.PayloadTooShort):
        codec.decode_ssu(bytes(32))
