"""A minimal scenario player for the fake TSS: timed value changes, faults and link loss.

A scenario is ``data/scenarios/<name>.yaml``: a list of steps, each at a time in scenario
seconds. ``SimDriver`` runs the fault rules (dynamics.py) on the fake's state at about 10 Hz
and applies each step when its time comes. ``speed`` > 1 runs scenario time faster than real
time, so tests see a whole failure in seconds. The full mission driver is M3; this player only
ever drives the built-in fake, never a real TSS.

Step keys (one or more per step):
    at: 2.0                  seconds from the start (scenario time)
    fault: fan               turn a fault on (fan, oxy, scrubber, power)
    clear: fan               turn it off
    set: {telemetry.heart_rate: 152, status.started: false, dcu.fan: false}
                             paths that exist in the fake's state; not error.* or the fan rpms,
                             which the fault rules own (use fault: instead)
    link: lost | back        the fake stops answering and pushing, or starts again
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from suits.paths import DATA_DIR
from suits.sim.dynamics import Dynamics, FaultName
from suits.sim.fake_tss import FakeTss, default_state

log = logging.getLogger(__name__)

SCENARIOS_DIR = DATA_DIR / "scenarios"
TICK_S = 0.1  # real seconds between dynamics updates
FAILED_TICKS_LIMIT = 3  # ticks in a row that fail before the driver stops (and /health says so)
# Set by dynamics.py on every tick: a scenario setting them would be undone at once.
OWNED_BY_RULES = ("error.", "telemetry.fan_pri_rpm", "telemetry.fan_sec_rpm")


class ScenarioError(ValueError):
    """A scenario file is missing or wrong. The message names the file and the step."""


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    at: float = Field(ge=0)
    fault: FaultName | None = None
    clear: FaultName | None = None
    set: dict[str, Any] | None = None
    link: Literal["lost", "back"] | None = None

    @model_validator(mode="after")
    def _does_something(self) -> Step:
        if self.fault is None and self.clear is None and not self.set and self.link is None:
            raise ValueError("a step needs fault, clear, set or link")
        return self


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str = ""
    steps: list[Step] = Field(min_length=1)

    @property
    def length_s(self) -> float:
        return max(step.at for step in self.steps)


def scenario_path(name: str) -> Path:
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise ScenarioError(f"bad scenario name {name!r}")
    return SCENARIOS_DIR / f"{name}.yaml"


def available() -> list[str]:
    return sorted(p.stem for p in SCENARIOS_DIR.glob("*.yaml"))


def load_scenario(name: str, path: Path | None = None) -> Scenario:
    path = path or scenario_path(name)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ScenarioError(
            f"no scenario {name!r} ({path}); known: {', '.join(available()) or 'none'}"
        ) from None
    except (OSError, yaml.YAMLError) as exc:
        raise ScenarioError(f"{path}: cannot read: {exc}") from exc
    if not isinstance(raw, dict):
        raise ScenarioError(f"{path}: expected a mapping with 'steps'")
    try:
        scenario = Scenario.model_validate({"name": name, **raw})
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise ScenarioError(f"{path}: {problems}") from exc
    for index, step in enumerate(scenario.steps):
        for key in (step.set or {}):
            _check_path(path, index, key)
    return scenario


def _check_path(path: Path, index: int, key: str) -> None:
    """The path must name a value that exists in the fake's state (a typo would otherwise
    add a key nobody reads) and that the fault rules do not overwrite."""
    where = f"{path}: steps.{index}.set: {key!r}"
    if key.startswith(OWNED_BY_RULES):
        raise ScenarioError(f"{where} is set by the fault rules; use fault: instead")
    target: Any = default_state()
    for part in key.split("."):
        if not isinstance(target, dict) or part not in target:
            raise ScenarioError(f"{where}: bad path, no such value in the fake TSS")
        target = target[part]
    if isinstance(target, dict):
        raise ScenarioError(f"{where}: bad path, names a section, not a value")


class SimDriver:
    """Runs the fault rules on the fake TSS and plays an optional scenario."""

    def __init__(self, fake: FakeTss, scenario: Scenario | None = None,
                 speed: float = 1.0) -> None:
        if not speed > 0:
            raise ValueError(f"speed must be positive, got {speed}")
        self.fake = fake
        self.dynamics = Dynamics(fake.state)
        self.scenario = scenario
        self.speed = speed
        self.elapsed_s = 0.0  # scenario time
        self._next = 0  # index of the next step to apply
        self._steps = sorted(scenario.steps, key=lambda s: s.at) if scenario else []

    @property
    def finished(self) -> bool:
        return self._next >= len(self._steps)

    def advance(self, dt_s: float) -> None:
        """Move scenario time on by ``dt_s``: apply due steps, then run the rules."""
        self.elapsed_s += dt_s
        while not self.finished and self._steps[self._next].at <= self.elapsed_s:
            step = self._steps[self._next]
            self._next += 1  # first: a step that fails is not retried every tick
            self._apply(step)
        self.dynamics.tick(dt_s)

    def _apply(self, step: Step) -> None:
        name = self.scenario.name if self.scenario else "?"
        log.info("scenario %s at %.1f s: %s", name, step.at,
                 step.model_dump(exclude_none=True, exclude={"at"}))
        if step.fault is not None:
            self.dynamics.set_fault(step.fault, True)
        if step.clear is not None:
            self.dynamics.set_fault(step.clear, False)
        for key, value in (step.set or {}).items():
            target = self.fake.state
            *parents, leaf = key.split(".")
            for part in parents:
                target = target[part]  # checked at load: the path exists
            target[leaf] = value
        if step.link is not None:
            self.fake.silent = step.link == "lost"

    async def run(self) -> None:
        """Run until cancelled. One bad tick is logged; FAILED_TICKS_LIMIT in a row end the
        task, so /health names it as dead instead of the sim silently freezing."""
        last = time.monotonic()
        failures = 0
        while True:
            await asyncio.sleep(TICK_S)
            now = time.monotonic()
            try:
                self.advance((now - last) * self.speed)
                failures = 0
            except Exception:
                failures += 1
                if failures >= FAILED_TICKS_LIMIT:
                    raise
                log.exception("sim dynamics tick failed (%d in a row)", failures)
            last = now
