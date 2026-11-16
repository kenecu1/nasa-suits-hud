"""When State is sent: heartbeat, change, and the 100 ms batching of decision B."""

import asyncio
import contextlib

from suits.contract import DcuPositions, LinkStatus, Mode, TssSnapshot
from suits.core.publisher import Publisher
from suits.core.store import Store

DCU = DcuPositions(batt="LOCAL", oxy="PRI", comm="A", fan="PRI", pump="CLOSED", co2="A")


class FakeSource:
    def __init__(self) -> None:
        self.o2 = 92.0

    def snapshot(self) -> TssSnapshot:
        return TssSnapshot(
            t=1000.0, link=LinkStatus.OK,
            ages={"telemetry": 0.1, "status": 0.1, "faults": 0.1, "dcu": 0.1, "uia": 0.1},
            telemetry={"oxy_pri_storage": self.o2}, started=True, faults=None, dcu=DCU, uia=None,
        )


@contextlib.asynccontextmanager
async def running(publisher: Publisher):
    task = asyncio.create_task(publisher.run())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def drain(queue: asyncio.Queue) -> list:
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


async def test_heartbeat_sends_even_without_change():
    publisher = Publisher(FakeSource().snapshot, Store(Mode.SIM), heartbeat_s=0.1)
    queue = publisher.subscribe()

    async with running(publisher):
        await asyncio.sleep(0.35)

    states = drain(queue)
    assert 3 <= len(states) <= 4  # beats at 0, 0.1, 0.2, 0.3
    assert [s.seq for s in states] == list(range(1, len(states) + 1))


async def test_a_burst_of_changes_becomes_one_message():
    source = FakeSource()
    publisher = Publisher(source.snapshot, Store(Mode.SIM), coalesce_s=0.1, heartbeat_s=10)
    queue = publisher.subscribe()

    async with running(publisher):
        await asyncio.sleep(0.05)
        drain(queue)  # the first heartbeat
        for value in (50.0, 40.0, 15.0):  # DCU, UIA and legacy replies landing close together
            source.o2 = value
            publisher.notify_change()
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.2)

    states = drain(queue)
    assert len(states) == 1
    assert states[0].suit.values["oxy_pri_storage"].value == 15.0


async def test_a_change_notice_without_new_content_sends_nothing():
    publisher = Publisher(FakeSource().snapshot, Store(Mode.SIM), coalesce_s=0.01, heartbeat_s=10)
    queue = publisher.subscribe()

    async with running(publisher):
        await asyncio.sleep(0.05)
        drain(queue)
        publisher.notify_change()
        await asyncio.sleep(0.1)

    assert drain(queue) == []


async def test_a_slow_subscriber_keeps_only_the_newest_states():
    source = FakeSource()
    publisher = Publisher(source.snapshot, Store(Mode.SIM))
    queue = publisher.subscribe()

    for value in range(10):
        source.o2 = 50.0 + value
        publisher.publish()

    states = drain(queue)
    assert len(states) <= 4
    assert states[-1].suit.values["oxy_pri_storage"].value == 59.0


async def test_a_new_subscriber_gets_the_latest_state_at_once():
    publisher = Publisher(FakeSource().snapshot, Store(Mode.SIM))
    publisher.publish(force=True)

    queue = publisher.subscribe()

    assert queue.get_nowait().seq == 1


async def test_an_error_while_publishing_does_not_end_the_loop():
    store = Store(Mode.SIM)
    real_commit = store.commit
    calls = []

    def commit_fails_once(state):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("a bug")
        return real_commit(state)

    store.commit = commit_fails_once
    publisher = Publisher(FakeSource().snapshot, store, heartbeat_s=0.05)
    queue = publisher.subscribe()

    async with running(publisher):
        await asyncio.sleep(0.3)

    assert len(drain(queue)) >= 2  # it kept beating after the failure


async def test_a_new_subscriber_is_not_handed_an_old_state():
    publisher = Publisher(FakeSource().snapshot, Store(Mode.SIM), heartbeat_s=1.0)
    publisher.publish(force=True)
    publisher._latest_at -= 10  # the loop has been stuck for 10 s

    queue = publisher.subscribe()

    assert queue.empty()
