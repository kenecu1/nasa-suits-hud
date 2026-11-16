"""The adapter against the fake TSS over real localhost UDP (acceptance 4 and 5)."""

import asyncio

import pytest

from suits.contract import LinkStatus
from suits.sim.fake_tss import FakeTss
from suits.tss import codec
from suits.tss.client import TssAddress, TssClient
from suits.tss.source import TssSource
from tests.helpers import wait_until


@pytest.fixture
async def fake():
    async with FakeTss() as tss:
        yield tss


@pytest.fixture
async def link(fake):
    source = TssSource()
    client = TssClient(source, TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port))
    yield source, client
    await client.stop()


def has_everything(source: TssSource) -> bool:
    snap = source.snapshot()
    return bool(snap.telemetry) and snap.dcu is not None and snap.uia is not None


# ---- acceptance 4: subscription ----


async def test_first_full_snapshot_arrives_within_3_s(fake, link):
    source, client = link
    client.start()

    await wait_until(lambda: has_everything(source), within=3)

    snap = source.snapshot()
    assert snap.dcu.oxy == "PRI"  # the fake's default oxygen switch is primary
    assert snap.uia.eva_power == "OFF"


async def test_a_dropped_subscribe_is_sent_again(fake, link):
    source, client = link
    fake.drop_subscribes = 1
    client.start()

    await wait_until(lambda: source.snapshot().dcu is not None, within=3)

    # DCU dropped once, then DCU again, then UIA
    assert fake.subscribes_received >= 3


async def test_ack_1_means_unassigned_but_legacy_values_still_arrive(fake, link):
    source, client = link
    fake.ack_result = codec.AckResult.UNASSIGNED
    client.start()

    await wait_until(lambda: source.snapshot().link == LinkStatus.UNASSIGNED, within=3)
    await wait_until(lambda: bool(source.snapshot().telemetry), within=3)

    snap = source.snapshot()
    assert snap.dcu is None  # no push without assignment
    assert snap.link == LinkStatus.UNASSIGNED  # unassigned beats a working legacy path


async def test_assigning_the_team_later_recovers_without_restart(fake, link):
    source, client = link
    fake.ack_result = codec.AckResult.UNASSIGNED
    client.start()
    await wait_until(lambda: source.snapshot().link == LinkStatus.UNASSIGNED, within=3)

    fake.ack_result = codec.AckResult.OK

    await wait_until(lambda: source.snapshot().dcu is not None, within=4)
    await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=3)


async def test_resubscribes_when_the_tss_forgets_us(fake, link):
    source, client = link
    client.subscription.resubscribe_after_s = 1.5
    client.start()
    await wait_until(lambda: source.snapshot().dcu is not None, within=3)

    fake.subscribers.clear()  # a TSS restart loses every subscription
    sent_before = fake.subscribes_received

    await wait_until(lambda: fake.subscribes_received > sent_before, within=3)
    await wait_until(lambda: bool(fake.subscribers), within=2)


# ---- acceptance 5: legacy path and link loss ----


async def test_telemetry_status_and_faults_are_parsed(fake, link):
    source, client = link
    fake.state["error"]["fan_error"] = True
    client.start()

    await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=3)

    snap = source.snapshot()
    assert snap.telemetry["oxy_pri_storage"] == 92.0
    assert len(snap.telemetry) == 23
    assert snap.started is True
    assert snap.faults.fan is True
    assert snap.faults.oxy is False
    assert {1, 2, 4} <= set(fake.legacy_gets)  # every section is polled


async def test_silent_tss_becomes_unreachable_within_3_s_and_age_grows(fake, link):
    source, client = link
    client.start()
    await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=3)

    fake.silent = True
    waited = await wait_until(lambda: source.snapshot().link == LinkStatus.UNREACHABLE, within=3)

    first = source.snapshot().age_s
    await asyncio.sleep(0.3)
    second = source.snapshot().age_s
    assert waited <= 3
    assert second > first
    assert source.snapshot().telemetry["oxy_pri_storage"] == 92.0  # last value kept


async def test_bad_json_gives_bad_data(fake, link):
    source, client = link
    client.start()
    await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=3)

    fake.bad_json = True

    await wait_until(lambda: source.snapshot().link == LinkStatus.BAD_DATA, within=2)
    assert source.decode_errors > 0


async def test_link_recovers_after_bad_json_stops(fake, link):
    source, client = link
    fake.bad_json = True
    client.start()
    await wait_until(lambda: source.snapshot().link == LinkStatus.BAD_DATA, within=3)

    fake.bad_json = False

    await wait_until(lambda: source.snapshot().link == LinkStatus.OK, within=3)
