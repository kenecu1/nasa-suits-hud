"""Link behaviour learned from the real TSS and from review: throughput, dead sockets, bad bytes."""

import asyncio
import logging
import socket

from suits.contract import STALE_AFTER_S, LinkStatus
from suits.sim.fake_tss import FakeTss
from suits.tss import codec
from suits.tss.client import TssAddress, TssClient
from suits.tss.source import TssSource
from suits.tss.subscription import Subscription
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
            await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=6)
    finally:
        await client.stop()


async def test_bad_binary_over_real_udp_does_not_stop_the_receive_loop():
    async with FakeTss() as fake:
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.start()
        try:
            await wait_until(lambda: source.snapshot().dcu is not None, within=3)
            good = bytes.fromhex("6af55d34001100010003000000000000e5")

            fake.send_raw(good[:-1] + b"\x00")  # bad checksum
            fake.send_raw(good[:5])  # too short
            await wait_until(lambda: source.decode_errors >= 2, within=2)

            fake.state["dcu"]["oxy"] = False
            await wait_until(lambda: source.snapshot().dcu.oxy == "SEC", within=3)
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
            await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=4)
        finally:
            await client.stop()


async def test_one_device_going_quiet_is_resubscribed_on_its_own():
    async with FakeTss() as fake:
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.subscription.resubscribe_after_s = 1.5
        client.start()
        try:
            await wait_until(lambda: source.snapshot().uia is not None, within=3)
            fake.subscribers.pop(2)  # the TSS forgets UIA only; DCU keeps arriving

            await wait_until(lambda: 2 in fake.subscribers, within=4)
        finally:
            await client.stop()


class _AckLandsWithTheTimeout(asyncio.Queue):
    """The first wait for an Ack times out, and the Ack for that send lands in the same
    event-loop turn, before the subscriber resumes. Seen live: real-tss-6293795.jsonl at 1.57 s
    has two Acks recorded just before a third Subscribe. Real timers cannot place it there
    reliably on every OS, so this queue does it on purpose."""

    def __init__(self) -> None:
        super().__init__()
        self.first = True

    async def get(self):
        if not self.first:
            return await super().get()
        self.first = False
        try:
            return await super().get()
        except asyncio.CancelledError:  # wait_for's timeout cancels us...
            self.put_nowait(codec.AckResult.OK)  # ...and the late Ack is already here
            raise


class _SilentEndpoint:
    """Counts Subscribes; the TSS behind it never answers again."""

    def __init__(self) -> None:
        self.closed = asyncio.Event()
        self.sent = 0

    def send(self, data: bytes) -> bool:
        self.sent += 1
        return True


async def test_a_late_ack_is_not_thrown_away():
    subscription = Subscription(TssSource(), "127.0.0.1", 9, retry_s=0.05)
    subscription._ack = _AckLandsWithTheTimeout()
    endpoint = _SilentEndpoint()

    subscribed = await asyncio.wait_for(subscription._subscribe(endpoint, codec.Device.DCU), 2)

    assert subscribed is True
    assert endpoint.sent == 2  # the first send timed out, the resend found the late Ack


def test_subscribe_retries_after_one_second_by_default():
    # the real TSS takes up to about a second to answer (tss-legacy-port-is-slow)
    assert Subscription(TssSource(), "127.0.0.1").retry_s == 1.0


async def sample_links(source: TssSource, seconds: float) -> list[str]:
    seen = []
    end = asyncio.get_running_loop().time() + seconds
    while asyncio.get_running_loop().time() < end:
        seen.append(source.snapshot().link)
        await asyncio.sleep(0.02)
    return seen


async def test_unassigned_does_not_flicker_when_one_ack_is_lost():
    # Against the real TSS an Ack takes up to ~1 s. Ack 1 -> wait 1 s -> Subscribe lost ->
    # 1 s retry -> late Ack: more than 2.5 s between two Ack 1s, while legacy data still flows.
    async with FakeTss() as fake:
        fake.ack_result = codec.AckResult.UNASSIGNED
        fake.ack_delay_s = 0.8
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.start()
        try:
            await wait_until(lambda: source.snapshot().link == LinkStatus.UNASSIGNED, within=3)
            fake.drop_subscribes = 1

            seen = await sample_links(source, 5)
        finally:
            await client.stop()

    assert fake.drop_subscribes == 0  # the lost Subscribe really happened
    assert bool(source.snapshot().telemetry)  # the legacy path kept working
    assert set(seen) == {LinkStatus.UNASSIGNED}, sorted(set(seen))


async def test_an_unassigned_tss_that_goes_silent_becomes_unreachable_within_3_s():
    async with FakeTss() as fake:
        fake.ack_result = codec.AckResult.UNASSIGNED
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.start()
        try:
            await wait_until(lambda: source.snapshot().link == LinkStatus.UNASSIGNED, within=3)
            fake.silent = True

            waited = await wait_until(
                lambda: source.snapshot().link == LinkStatus.UNREACHABLE, within=3
            )
        finally:
            await client.stop()

    assert waited <= 3


async def test_a_reply_later_than_the_timeout_does_not_let_requests_pile_up():
    # A late reply must not count as the answer to the next request on that socket,
    # or one more request is in flight after every timeout.
    async with FakeTss(legacy_service_s=0.5) as fake:
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.legacy.reply_timeout_s = 0.3
        client.start()
        try:
            await asyncio.sleep(4)
        finally:
            await client.stop()

    assert fake.legacy_max_queue <= 1
    assert len(fake.legacy_gets) >= 4  # it kept polling


async def test_a_tss_that_never_answers_is_reported_once(caplog):
    caplog.set_level(logging.INFO, logger="suits")
    async with FakeTss() as fake:
        fake.silent = True
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.legacy.reply_timeout_s = 0.2
        client.subscription.retry_s = 0.2
        client.start()
        try:
            await asyncio.sleep(3)
            fake.silent = False
            await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=5)
        finally:
            await client.stop()

    warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    legacy = [m for m in warnings if "legacy" in m and str(fake.legacy_port) in m]
    subscribe = [m for m in warnings if "Subscribe" in m and str(fake.sub_port) in m]
    assert len(legacy) == 1, warnings
    assert len(subscribe) == 1, warnings
    assert any("answering again" in r.getMessage() for r in caplog.records)


async def test_an_unexpected_error_does_not_end_the_link_loops():
    async with FakeTss() as fake:
        source = TssSource()
        client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
        client.legacy.reopen_after_s = 0.1
        client.subscription.reopen_after_s = 0.1

        def fail_once(method):
            calls = []

            async def wrapper(*args, **kwargs):
                calls.append(1)
                if len(calls) == 1:
                    raise RuntimeError("a bug")
                return await method(*args, **kwargs)

            return wrapper

        client.legacy._request = fail_once(client.legacy._request)
        client.subscription._serve = fail_once(client.subscription._serve)
        client.start()
        try:
            await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=5)
            assert all(not t.done() for t in client.tasks)
        finally:
            await client.stop()
