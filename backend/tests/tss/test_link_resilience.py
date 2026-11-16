"""Link behaviour learned from the real TSS and from review: throughput, dead sockets, bad bytes."""

import asyncio
import socket

from suits.contract import STALE_AFTER_S, LinkStatus
from suits.sim.fake_tss import FakeTss
from suits.tss.client import TssAddress, TssClient
from suits.tss.source import TssSource

from tests.helpers import wait_until


def free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def test_legacy_poller_never_queues_requests_on_a_slow_tss():
    # The real TSS serves one legacy request per ~1.2 s per port. Sending faster built a queue
    # there and replies arrived later and later while looking fresh (docs/notes).
    async with FakeTss(legacy_service_s=0.3) as fake:
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.start()
        try:
            await asyncio.sleep(4)
            snap = source.snapshot()
        finally:
            await client.stop()

    assert fake.legacy_max_queue <= 1
    assert snap.ages["telemetry"] < STALE_AFTER_S["telemetry"]
    assert snap.link == LinkStatus.OK


async def test_link_recovers_when_the_tss_starts_after_the_backend():
    # Sending to a closed port gives "port unreachable"; on Windows' Proactor loop the socket
    # then goes deaf unless it is reopened.
    sub_port, legacy_port = free_udp_port(), free_udp_port()
    source = TssSource()
    client = TssClient(source, TssAddress("127.0.0.1", sub_port, legacy_port))
    client.subscription.reopen_after_s = 0.2
    client.legacy.reopen_after_s = 0.2
    client.start()
    try:
        await asyncio.sleep(1.5)  # several sends into nothing
        assert source.snapshot().link == LinkStatus.UNREACHABLE

        async with FakeTss(sub_port=sub_port, legacy_port=legacy_port):
            await wait_until(lambda: source.snapshot().link == LinkStatus.OK, timeout=6)
    finally:
        await client.stop()


async def test_bad_binary_over_real_udp_does_not_stop_the_receive_loop():
    async with FakeTss() as fake:
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.start()
        try:
            await wait_until(lambda: source.snapshot().dcu is not None, timeout=3)
            good = bytes.fromhex("6af55d34001100010003000000000000e5")

            fake.send_raw(good[:-1] + b"\x00")  # bad checksum
            fake.send_raw(good[:5])  # too short
            await wait_until(lambda: source.decode_errors >= 2, timeout=2)

            fake.state["dcu"]["oxy"] = False
            await wait_until(lambda: source.snapshot().dcu.oxy == "SEC", timeout=3)
        finally:
            await client.stop()


async def test_a_failing_recorder_does_not_stop_the_link():
    def broken_tap(direction, channel, data):
        raise OSError("disk full")

    async with FakeTss() as fake:
        source = TssSource()
        client = TssClient(
            source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port), tap=broken_tap
        )
        client.start()
        try:
            await wait_until(lambda: source.snapshot().link == LinkStatus.OK, timeout=4)
        finally:
            await client.stop()


async def test_one_device_going_quiet_is_resubscribed_on_its_own():
    async with FakeTss() as fake:
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.subscription.resubscribe_after_s = 1.5
        client.start()
        try:
            await wait_until(lambda: source.snapshot().uia is not None, timeout=3)
            fake.subscribers.pop(2)  # the TSS forgets UIA only; DCU keeps arriving

            await wait_until(lambda: 2 in fake.subscribers, timeout=4)
        finally:
            await client.stop()
