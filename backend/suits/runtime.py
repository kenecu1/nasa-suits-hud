"""Wiring: build the pieces for one mode, start them, stop them. No mission logic.

sim     fake TSS on localhost  -> TssClient -> TssSource -> Store -> Publisher
replay  recording file         -> Replayer  -> TssSource -> Store -> Publisher
live    NASA's TSS             -> TssClient -> TssSource -> Store -> Publisher
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field

from suits.contract import Mode
from suits.core.publisher import Publisher
from suits.core.store import Store
from suits.paths import RECORDINGS_DIR
from suits.settings import Settings
from suits.sim.fake_tss import FakeTss
from suits.tss.client import TssAddress, TssClient
from suits.tss.recorder import Recorder, Replayer
from suits.tss.source import TssSource

log = logging.getLogger(__name__)


@dataclass
class Runtime:
    settings: Settings
    source: TssSource
    publisher: Publisher
    fake_tss: FakeTss | None = None  # sim mode only: tests change its values
    client: TssClient | None = None
    replayer: Replayer | None = None
    recorder: Recorder | None = None
    tasks: list[asyncio.Task] = field(default_factory=list)

    async def stop(self) -> None:
        for task in self.tasks:
            task.cancel()
        for task in self.tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if self.client is not None:
            await self.client.stop()
        if self.fake_tss is not None:
            await self.fake_tss.stop()
        if self.recorder is not None:
            self.recorder.close()


async def start_runtime(settings: Settings) -> Runtime:
    recorder = None
    if settings.record and settings.mode != Mode.REPLAY:
        name = f"{settings.mode.value}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        recorder = Recorder(RECORDINGS_DIR / name)
        log.info("recording raw TSS datagrams to %s", recorder.path)

    replayer = None
    if settings.mode == Mode.REPLAY:
        assert settings.recording is not None  # Settings.from_env checks this
        replayer = Replayer(settings.recording, settings.replay_speed)
    # in replay, time is the recording's, so the link goes stale when the recording ends
    source = TssSource(clock=replayer.clock, wall=replayer.clock) if replayer else TssSource()
    publisher = Publisher(source.snapshot, Store(settings.mode))
    source.on_change = publisher.notify_change
    runtime = Runtime(settings, source, publisher, replayer=replayer, recorder=recorder)

    if settings.mode == Mode.SIM:
        fake = FakeTss()
        await fake.start()
        runtime.fake_tss = fake
        address = TssAddress("127.0.0.1", fake.sub_port, fake.legacy_port)
    elif settings.mode == Mode.LIVE:
        assert settings.tss_host is not None
        address = TssAddress.for_team(settings.tss_host, settings.tss_team)
    else:
        address = None

    if address is not None:
        runtime.client = TssClient(source, address, tap=recorder)
        runtime.client.start()
        log.info("TSS link (%s): %s", settings.mode.value, address)
    if replayer is not None:
        runtime.tasks.append(asyncio.create_task(replayer.run(source), name="replay"))
        log.info("replaying %s at %sx", replayer.path, replayer.speed)

    runtime.tasks.append(asyncio.create_task(publisher.run(), name="publisher"))
    return runtime
