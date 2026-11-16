"""TssSnapshot -> State. Pure: no sockets, no clocks of its own.

Decides levels (via levels.py and data/ranges.json) and staleness. A section older than
STALE_AFTER_S is stale: suit values keep their last number with level "stale"; switch
positions, faults and "started" become None (unknown), because a stale switch is not a fact.
"""

from __future__ import annotations

from typing import Any

from suits.contract import (
    STALE_AFTER_S,
    Eva,
    Level,
    Link,
    Mode,
    Section,
    State,
    Suit,
    SuitValue,
    TssSnapshot,
)
from suits.core.levels import classify, load_ranges


def _fresh(snapshot: TssSnapshot, section: Section) -> bool:
    age = snapshot.ages.get(section)
    return age is not None and age <= STALE_AFTER_S[section]


def suit_values(snapshot: TssSnapshot, ranges: dict[str, Any]) -> dict[str, SuitValue]:
    """Every value named in ranges.json ("ranges" and "unranged"), always all of them."""
    fresh = _fresh(snapshot, "telemetry")
    # Before the EVA starts the TSS reads zeros, so no alarms. Only a fresh "not started"
    # silences them: unknown or stale status counts as started, so alarms stay on.
    started = not (snapshot.started is False and _fresh(snapshot, "status"))
    margin = ranges["caution_margin"]
    values: dict[str, SuitValue] = {}
    for name, spec in {**ranges["ranges"], **ranges.get("unranged", {})}.items():
        value = snapshot.telemetry.get(name)
        if value is None:
            level = Level.UNKNOWN
        elif not fresh:
            level = Level.STALE
        elif not started or "check" not in spec:
            level = Level.NOMINAL
        else:
            level = Level(classify(value, spec, margin))
        values[name] = SuitValue(value=value, unit=spec["unit"], level=level)
    return values


def build_state(
    snapshot: TssSnapshot, ranges: dict[str, Any], mode: Mode, seq: int
) -> State:
    values = suit_values(snapshot, ranges)
    return State(
        seq=seq,
        t=snapshot.t,
        link=Link(tss=snapshot.link, age_s=snapshot.age_s, mode=mode),
        eva=Eva(
            started=snapshot.started if _fresh(snapshot, "status") else None,
            elapsed_s=snapshot.elapsed_s if _fresh(snapshot, "telemetry") else None,
            phase=None,
        ),
        suit=Suit(
            values=values,
            faults=snapshot.faults if _fresh(snapshot, "faults") else None,
        ),
        dcu=snapshot.dcu if _fresh(snapshot, "dcu") else None,
        uia=snapshot.uia if _fresh(snapshot, "uia") else None,
    )


def content_key(state: State) -> str:
    """What counts as a change: everything except the counters and clocks."""
    return state.model_dump_json(exclude={"seq": True, "t": True, "link": {"age_s"}})


class Store:
    """Holds the ranges and the message counter; builds numbered States."""

    def __init__(self, mode: Mode, ranges: dict[str, Any] | None = None) -> None:
        self.mode = mode
        self.ranges = ranges if ranges is not None else load_ranges()
        self.seq = 0

    def preview(self, snapshot: TssSnapshot) -> State:
        """The State the next send would carry, without using up a sequence number."""
        return build_state(snapshot, self.ranges, self.mode, self.seq + 1)

    def commit(self, state: State) -> State:
        self.seq = state.seq
        return state
