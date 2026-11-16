"""The fake TSS itself: later milestones' tests are only as good as this double."""

import asyncio
import socket
import struct

import pytest

from suits.sim.fake_tss import LEGACY_SETS, FakeTss
from suits.tss import codec


class Udp:
    """A plain blocking UDP client run in a thread, so the fake is tested from outside."""

    def __init__(self, port: int) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2)
        self.addr = ("127.0.0.1", port)

    async def ask(self, data: bytes) -> bytes:
        def roundtrip() -> bytes:
            self.sock.sendto(data, self.addr)
            return self.sock.recv(65535)

        return await asyncio.to_thread(roundtrip)

    def close(self) -> None:
        self.sock.close()


@pytest.fixture
async def fake():
    async with FakeTss() as tss:
        yield tss


@pytest.mark.parametrize(
    ("command", "path", "value", "expected"),
    [
        (2012, ("dcu", "oxy"), 0.0, False),
        (2011, ("dcu", "batt", "lu"), 1.0, True),
        (2001, ("uia", "eva1_power"), 1.0, True),
        (2010, ("uia", "depress"), 1.0, True),
        (2017, ("imu", "posx"), -5600.5, -5600.5),
        (2020, ("spec", "id"), 7.0, 7),
    ],
)
async def test_legacy_set_changes_state_and_replies_ok(fake, command, path, value, expected):
    udp = Udp(fake.legacy_port)
    try:
        reply = await udp.ask(codec.build_legacy_set(0, command, value))
    finally:
        udp.close()

    target = fake.state
    for key in path:
        target = target[key]
    assert reply == codec.LEGACY_SET_OK
    assert target == pytest.approx(expected)


def test_every_command_the_notes_list_is_accepted():
    assert set(LEGACY_SETS) == set(range(2001, 2005)) | set(range(2009, 2021))


async def test_unknown_set_is_refused(fake):
    udp = Udp(fake.legacy_port)
    try:
        reply = await udp.ask(codec.build_legacy_set(0, 2005, 1.0))  # eva2: not ours
    finally:
        udp.close()

    assert reply == b"\x00\x00\x00\x00"


async def test_legacy_get_returns_the_bare_section(fake):
    udp = Udp(fake.legacy_port)
    try:
        reply = await udp.ask(codec.build_legacy_get(0, 2))
    finally:
        udp.close()

    assert codec.parse_legacy_reply(reply) == {"started": True}


@pytest.mark.parametrize("result", list(codec.AckResult))
async def test_subscribe_is_answered_with_the_configured_ack(fake, result):
    fake.ack_result = result
    udp = Udp(fake.sub_port)
    try:
        reply = await udp.ask(codec.build_subscribe(0, codec.Device.DCU))
    finally:
        udp.close()

    assert codec.parse_ack(codec.decode(reply)) == result
    assert (codec.Device.DCU in fake.subscribers) == (result == codec.AckResult.OK)


async def test_subscribe_to_an_unknown_device_gets_ack_2(fake):
    udp = Udp(fake.sub_port)
    try:
        bad = codec.encode(0, codec.Device.TEAM, codec.Code.SUBSCRIBE, struct.pack(">H", 99))
        reply = await udp.ask(bad)
    finally:
        udp.close()

    assert codec.parse_ack(codec.decode(reply)) == codec.AckResult.REJECTED


async def test_a_subscriber_gets_pushes_with_the_states_flags(fake):
    fake.state["dcu"]["pump"] = True
    udp = Udp(fake.sub_port)
    try:
        await udp.ask(codec.build_subscribe(0, codec.Device.DCU))
        fake.push_now()
        packet = codec.decode(await asyncio.to_thread(udp.sock.recv, 65535))
    finally:
        udp.close()

    assert packet.device == codec.Device.DCU
    assert codec.decode_dcu(packet.data).pump == 1
