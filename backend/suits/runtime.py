"""Wiring: build the pieces for one mode, start them, stop them. No mission logic.

sim     fake TSS on localhost  -> TssClient -> TssSource -> Store -> Publisher
        (+ SimDriver: the TSS's fault rules and an optional scenario, on the fake's state)
replay  recording file         -> Replayer  -> TssSource -> Store -> Publisher
live    NASA's TSS             -> TssClient -> TssSource -> Store -> Publisher
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from suits.contract import Mode
from suits.core.publisher import Publisher
from suits.core.store import Store
from suits.paths import RECORDINGS_DIR
from suits.settings import Settings
from suits.sim.fake_tss import FakeTss
from suits.sim.scenarios import SimDriver, load_scenario
from suits.tasks import cancel_all, dead, spawn
from suits.tss.client import TssAddress, TssClient
from suits.tss.recorder import Recorder, Replayer
from suits.tss.source import TssSource

log = logging.getLogger(__name__)


@dataclass
class Runtime:
    settings: Settings
    source: TssSource
    store: Store
    publisher: Publisher
    fake_tss: FakeTss | None = None  # sim mode only: tests change its values
    sim: SimDriver | None = None  # sim mode only: fault rules and the scenario
    client: TssClient | None = None
    replayer: Replayer | None = None
    recorder: Recorder | None = None
    tasks: list[asyncio.Task] = field(default_factory=list)

    async def stop(self) -> None:
        """Stop everything that was started, even if some part failed."""
        await cancel_all(self.tasks)
        self.tasks = []
        steps = [
            self.client.stop() if self.client else None,
            self.fake_tss.stop() if self.fake_tss else None,
        ]
        for step in steps:
            if step is None:
                continue
            try:
                await step
            except Exception:
                log.exception("error while stopping")
        if self.recorder is not None:
            self.recorder.close()

    def dead_tasks(self) -> list[str]:
        """Background tasks that ended on their own: the backend is degraded."""
        client_tasks = self.client.tasks if self.client else []
        return dead([*self.tasks, *client_tasks])


# The built-in fake answers the legacy port a little slowly, so the one-request-at-a-time
# poller is exercised in sim mode too (the real TSS takes about 1.2 s per request).
SIM_LEGACY_SERVICE_S = 0.3


async def start_runtime(settings: Settings) -> Runtime:
    replayer = None
    if settings.mode == Mode.REPLAY:
        assert settings.recording is not None  # Settings.from_env checks this
        replayer = Replayer(settings.recording, settings.replay_speed)
    # in replay, time is the recording's, so the link goes stale when the recording ends
    source = TssSource(clock=replayer.clock, wall=replayer.clock) if replayer else TssSource()
    store = Store(settings.mode)
    publisher = Publisher(source.snapshot, store)
    source.on_change = publisher.notify_change
    runtime = Runtime(settings, source, store, publisher, replayer=replayer)
    try:
        await _start(runtime, settings)
    except BaseException:
        try:
            await runtime.stop()  # nothing half-started is left open
        except Exception:
            log.exception("cleanup after a failed start also failed")  # keep the real reason
        raise
    return runtime


async def _start(runtime: Runtime, settings: Settings) -> None:
    if settings.record and settings.mode != Mode.REPLAY:
        name = f"{settings.mode.value}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        runtime.recorder = Recorder(RECORDINGS_DIR / name)
        log.info("recording raw TSS datagrams to %s", runtime.recorder.path)

    address: TssAddress | None = None
    if settings.mode == Mode.SIM:
        runtime.fake_tss = FakeTss(legacy_service_s=SIM_LEGACY_SERVICE_S)
        await runtime.fake_tss.start()
        scenario = load_scenario(settings.scenario) if settings.scenario else None
        runtime.sim = SimDriver(runtime.fake_tss, scenario, settings.scenario_speed)
        runtime.tasks.append(spawn(runtime.sim.run(), "sim"))
        if scenario is not None:
            log.info("playing scenario %s at %sx", scenario.name, settings.scenario_speed)
        address = TssAddress("127.0.0.1", runtime.fake_tss.sub_port, runtime.fake_tss.legacy_port)
    elif settings.mode == Mode.LIVE:
        assert settings.tss_host is not None
        address = TssAddress.for_team(settings.tss_host, settings.tss_team)

    if address is not None:
        runtime.client = TssClient(runtime.source, address, tap=runtime.recorder)
        runtime.client.start()
        log.info("TSS link (%s): %s", settings.mode.value, address)
    if runtime.replayer is not None:
        runtime.tasks.append(spawn(runtime.replayer.run(runtime.source), "replay"))
        log.info("replaying %s at %sx", runtime.replayer.path, runtime.replayer.speed)

    runtime.tasks.append(spawn(runtime.publisher.run(), "publisher"))
