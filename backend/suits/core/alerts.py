"""Levels, fault flags and link status -> alerts (M2 scope 1-4; decisions C, D, E in
docs/briefs/M2.md).

The AlertBook is the backend's memory between snapshots: how many samples in a row each
problem was off nominal, when each alert started and whether it was acknowledged. It is a
value: ``step(book, inputs, rules)`` and ``ack(book, id)`` return a new book and never change
the old one. Nothing here reads a clock, a socket or a file after loading the rules, so tests
drive it one sample at a time.

* One sample is one new telemetry arrival (decision C). Calling ``step`` twice with the same
  arrival counts it once, so the publisher may build a State as often as it likes.
* A problem rule's values raise an alert after ``RAISE_AFTER`` samples off nominal and clear
  it after ``CLEAR_AFTER`` nominal samples. Its fault flag raises a warning at once and clears
  on the first all-clear. Severity is the worst of its inputs.
* Old data raises and holds nothing: while the link is unreachable there is exactly one alert
  (the link), and a stale value resets its problem. Before the EVA starts (a fresh "not
  started") there are no suit alerts; unknown counts as started (decision E).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NamedTuple, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from suits.contract import (
    Alert,
    DcuPositions,
    Level,
    LinkStatus,
    Severity,
    SuitFaults,
    SuitValue,
)
from suits.paths import DATA_DIR

ALERTS_FILE = DATA_DIR / "alerts.json"

RAISE_AFTER = 2  # samples off nominal before a level raises an alert
CLEAR_AFTER = 3  # nominal samples before it clears

LINK_ID = "link"
DATA_ID = "data"
GENERIC_PREFIX = "value."

_RANK = {Severity.WARNING: 2, Severity.CAUTION: 1}


class AlertsError(ValueError):
    """data/alerts.json is missing or wrong. The message names the file and the problem."""


# ---- the rules file ----


class _Entry(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


FaultName = Literal["fan", "oxy", "power", "scrubber"]
LinkKey = Literal["unreachable", "unassigned", "bad_data", "stale"]


class ValueInput(_Entry):
    """One ranged value, or the one the DCU switch selects (``switch`` + ``by_position``)."""

    value: str | None = None
    switch: str | None = None
    by_position: dict[str, str] | None = None
    label: str = Field(min_length=1)  # "{position}" is replaced by the switch position

    @model_validator(mode="after")
    def _one_kind(self) -> ValueInput:
        if (self.value is None) == (self.switch is None):
            raise ValueError("give either value, or switch with by_position")
        if (self.switch is None) != (self.by_position is None):
            raise ValueError("switch and by_position go together")
        return self

    def names(self) -> list[str]:
        return [self.value] if self.value is not None else list((self.by_position or {}).values())


class ProblemRule(_Entry):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    action: str = Field(min_length=1)
    fault: FaultName | None
    values: list[ValueInput]


class Generic(_Entry):
    action: str = Field(min_length=1)


class Text(_Entry):
    severity: Severity = Field(strict=False)  # strict mode would want an enum, not "warning"
    title: str = Field(min_length=1)
    action: str = Field(min_length=1)


class AlertsFile(_Entry):
    source: str | None = Field(default=None, alias="_source")
    how_it_works: str | None = Field(default=None, alias="_how_it_works")
    rules: list[ProblemRule] = Field(min_length=1)
    generic: Generic
    link: dict[LinkKey, Text]
    data: Text

    @model_validator(mode="after")
    def _complete(self) -> AlertsFile:
        missing = sorted(set(get_args(LinkKey)) - set(self.link))
        if missing:
            raise ValueError(f"link has no text for {', '.join(missing)}")
        ids = [r.id for r in self.rules]
        clash = sorted({i for i in ids if ids.count(i) > 1 or i in (LINK_ID, DATA_ID)}
                       | {i for i in ids if i.startswith(GENERIC_PREFIX)})
        if clash:
            raise ValueError(f"rule ids not allowed or repeated: {', '.join(clash)}")
        return self


@dataclass(frozen=True)
class LevelRule:
    """A problem watched through levels and maybe a fault flag. Generic rules have one value."""

    id: str
    label: str
    action: str
    fault: FaultName | None
    values: tuple[ValueInput, ...]


@dataclass(frozen=True)
class Rules:
    problems: tuple[LevelRule, ...]  # the file's rules, then one generic rule per other value
    link: Mapping[LinkKey, Text]
    data: Text


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    seen: dict = {}
    for key, value in pairs:
        if key in seen:
            raise AlertsError(f"duplicate key {key!r}")
        seen[key] = value
    return seen


def _label(name: str) -> str:
    return name.replace("_", " ").upper()


def load_rules(ranges: dict, path: Path | None = None) -> Rules:
    """Read and check data/alerts.json against the ranges (from levels.load_ranges)."""
    path = path or ALERTS_FILE
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f, object_pairs_hook=_no_duplicate_keys)
        parsed = AlertsFile.model_validate(raw)
    except AlertsError as exc:
        raise AlertsError(f"{path}: {exc}") from exc
    except OSError as exc:
        raise AlertsError(f"{path}: cannot read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AlertsError(f"{path}: not valid JSON: {exc}") from exc
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise AlertsError(f"{path}: {problems}") from exc

    ranged = ranges["ranges"]
    claimed: set[str] = set()
    for rule in parsed.rules:
        for value in rule.values:
            _check_value(path, rule.id, value, ranged)
            claimed.update(value.names())
    generic = tuple(
        LevelRule(
            id=f"{GENERIC_PREFIX}{name}",
            label=_label(name),
            action=parsed.generic.action,
            fault=None,
            values=(ValueInput(value=name, label=_label(name)),),
        )
        for name in ranged
        if name not in claimed
    )
    problems = tuple(
        LevelRule(r.id, r.label, r.action, r.fault, tuple(r.values)) for r in parsed.rules
    )
    return Rules(problems=problems + generic, link=dict(parsed.link), data=parsed.data)


def _check_value(path: Path, rule_id: str, value: ValueInput, ranged: dict) -> None:
    unknown = [n for n in value.names() if n not in ranged]
    if unknown:
        raise AlertsError(f"{path}: rule {rule_id}: {', '.join(unknown)} not in ranges.json")
    if value.switch is None:
        return
    if value.switch not in DcuPositions.model_fields:
        raise AlertsError(f"{path}: rule {rule_id}: no DCU switch {value.switch!r}")
    positions = set(get_args(DcuPositions.model_fields[value.switch].annotation))
    if set(value.by_position or {}) != positions:
        raise AlertsError(
            f"{path}: rule {rule_id}: by_position must name exactly {sorted(positions)}"
        )


# ---- inputs and memory ----


@dataclass(frozen=True)
class AlertInputs:
    """What one step looks at. Built by core/store.py from the snapshot and the State."""

    t: float  # State.t: becomes ``since`` of a new alert
    telemetry_arrival: int | None  # TssSnapshot.arrivals["telemetry"]; None = never arrived
    values: Mapping[str, SuitValue]
    faults: SuitFaults | None  # None = unknown or stale
    dcu: DcuPositions | None  # None = unknown or stale: switch-selected values are skipped
    link: LinkStatus
    eva_started: bool | None  # None = unknown, counts as started
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class Track:
    """Hysteresis memory of one problem's values. Counts are samples in a row."""

    off: int = 0  # some input caution or warning
    warn: int = 0  # some input warning
    calm: int = 0  # no input warning
    ok: int = 0  # every known input nominal
    raised: Severity | None = None  # the values' part of the alert, None = not raised


@dataclass(frozen=True)
class AlertBook:
    """Treat as immutable: step and ack build new dicts, never change these."""

    tracks: Mapping[str, Track] = field(default_factory=dict)
    active: Mapping[str, Alert] = field(default_factory=dict)
    telemetry_seen: int | None = None  # the arrival the tracks have counted

    def alerts(self) -> tuple[Alert, ...]:
        """Unacknowledged first, then warning before caution, then newest first."""
        return tuple(
            sorted(
                self.active.values(),
                key=lambda a: (a.acked, -_RANK[a.severity], -a.since, a.id),
            )
        )


class Watched(NamedTuple):
    name: str
    label: str
    level: Level
    value: float | None
    unit: str


# ---- one step ----


def step(book: AlertBook, inputs: AlertInputs, rules: Rules) -> AlertBook:
    lost = inputs.link == LinkStatus.UNREACHABLE
    suit_on = not lost and inputs.eva_started is not False
    new_sample = (
        inputs.telemetry_arrival is not None and inputs.telemetry_arrival != book.telemetry_seen
    )

    wanted: dict[str, tuple[Severity, str, str]] = {}
    tracks: dict[str, Track] = {}
    for rule in rules.problems:
        watched = _watched(rule, inputs)
        track = book.tracks.get(rule.id, Track())
        if not suit_on or any(w.level == Level.STALE for w in watched):
            track = Track()  # old data raises and holds nothing
        elif new_sample:
            track = _advance(track, _worst(w.level for w in watched))
        if track != Track():
            tracks[rule.id] = track
        fault = (
            suit_on
            and rule.fault is not None
            and inputs.faults is not None
            and bool(getattr(inputs.faults, rule.fault))
        )
        severity = _worse(track.raised, Severity.WARNING if fault else None)
        if severity is not None:
            title = _value_title(watched) if track.raised else f"{rule.label} FAULT"
            wanted[rule.id] = (severity, title, rule.action)

    link = _link_text(inputs, rules)
    if link is not None:
        wanted[LINK_ID] = (link.severity, link.title, link.action)
    if inputs.missing and not lost:
        wanted[DATA_ID] = _data_text(inputs.missing, rules.data)

    active: dict[str, Alert] = {}
    for alert_id, (severity, title, action) in wanted.items():
        old = book.active.get(alert_id)
        escalated = old is not None and _RANK[severity] > _RANK[old.severity]
        active[alert_id] = Alert(
            id=alert_id,
            severity=severity,
            title=title,
            action=action,
            since=inputs.t if old is None else old.since,
            # a caution that becomes a warning must be seen again
            acked=old is not None and old.acked and not escalated,
        )
    seen = inputs.telemetry_arrival if inputs.telemetry_arrival is not None else book.telemetry_seen
    return AlertBook(tracks=tracks, active=active, telemetry_seen=seen)


def ack(book: AlertBook, alert_id: str | None = None) -> tuple[AlertBook, str | None]:
    """Acknowledge ``alert_id`` if it is listed, or the top unacknowledged alert if None.

    Returns the new book and the id that was acknowledged, or None if nothing changed (the id
    is not listed, it was already acknowledged, or nothing is unacknowledged).
    """
    if alert_id is None:
        alert_id = next((a.id for a in book.alerts() if not a.acked), None)
    alert = book.active.get(alert_id) if alert_id is not None else None
    if alert is None or alert.acked:
        return book, None
    active = {**book.active, alert.id: alert.model_copy(update={"acked": True})}
    return AlertBook(tracks=book.tracks, active=active, telemetry_seen=book.telemetry_seen), alert.id


# ---- helpers ----


def _watched(rule: LevelRule, inputs: AlertInputs) -> list[Watched]:
    """Each input this rule watches now.

    A switch-selected value is watched only when the switch position is known.
    """
    out = []
    for item in rule.values:
        if item.switch is None:
            name, label = item.value, item.label
        else:
            if inputs.dcu is None:
                continue
            position = getattr(inputs.dcu, item.switch)
            name = (item.by_position or {})[position]
            label = item.label.replace("{position}", position)
        assert name is not None
        value = inputs.values.get(name)
        if value is None:  # store.py always lists every ranged value; be safe anyway
            out.append(Watched(name, label, Level.UNKNOWN, None, ""))
        else:
            out.append(Watched(name, label, value.level, value.value, value.unit))
    return out


def _worst(levels) -> Level | None:
    """The worst known level, or None if nothing is known (unknown values say nothing)."""
    known = [lv for lv in levels if lv in (Level.NOMINAL, Level.CAUTION, Level.WARNING)]
    if not known:
        return None
    if Level.WARNING in known:
        return Level.WARNING
    if Level.CAUTION in known:
        return Level.CAUTION
    return Level.NOMINAL


def _advance(track: Track, worst: Level | None) -> Track:
    if worst is None:
        return track  # no information in this sample
    if worst == Level.NOMINAL:
        off, warn, calm, ok = 0, 0, track.calm + 1, track.ok + 1
    else:
        off, ok = track.off + 1, 0
        warn = track.warn + 1 if worst == Level.WARNING else 0
        calm = 0 if worst == Level.WARNING else track.calm + 1
    raised = track.raised
    if raised is None:
        if off >= RAISE_AFTER:
            raised = Severity.WARNING if warn >= RAISE_AFTER else Severity.CAUTION
    elif ok >= CLEAR_AFTER:
        raised = None
    elif raised == Severity.CAUTION and warn >= RAISE_AFTER:
        raised = Severity.WARNING
    elif raised == Severity.WARNING and calm >= CLEAR_AFTER:
        raised = Severity.CAUTION
    return Track(off=off, warn=warn, calm=calm, ok=ok, raised=raised)


def _worse(a: Severity | None, b: Severity | None) -> Severity | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if _RANK[a] >= _RANK[b] else b


_LEVEL_ORDER = {Level.WARNING: 0, Level.CAUTION: 1, Level.NOMINAL: 2}


def _value_title(watched: list[Watched]) -> str:
    """'<label> <value> <unit>' of the worst input now, e.g. 'FAN PRI 21500 rpm'."""
    known = [w for w in watched if w.level in _LEVEL_ORDER and w.value is not None]
    if not known:
        return watched[0].label if watched else "?"
    worst = min(known, key=lambda w: _LEVEL_ORDER[w.level])
    return f"{worst.label} {_number(worst.value)} {worst.unit}".rstrip()


def _number(value: float | None) -> str:
    if value is None:
        return "?"
    if abs(value) >= 100:
        return f"{value:.0f}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _link_text(inputs: AlertInputs, rules: Rules) -> Text | None:
    if inputs.link == LinkStatus.UNREACHABLE:
        return rules.link["unreachable"]
    if inputs.link == LinkStatus.UNASSIGNED:
        return rules.link["unassigned"]
    if inputs.link == LinkStatus.BAD_DATA and not inputs.missing:
        return rules.link["bad_data"]  # missing names have their own, more precise alert
    if inputs.link == LinkStatus.STALE and any(
        v.level == Level.STALE for v in inputs.values.values()
    ):
        return rules.link["stale"]  # suit values are old; an old status or fault alone is not
    return None


def _data_text(missing: tuple[str, ...], text: Text) -> tuple[Severity, str, str]:
    count = len(missing)
    title = text.title.replace("{count}", str(count)).replace(
        "{fields}", "FIELD" if count == 1 else "FIELDS"
    )
    return text.severity, title, text.action.replace("{names}", ", ".join(missing))
