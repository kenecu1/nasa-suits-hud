"""TssSnapshot -> State. Pure: no sockets, no clocks of its own.

Decides levels (via levels.py and data/ranges.json) and staleness. A section older than
STALE_AFTER_S is stale: suit values keep their last number with level "stale"; switch
positions, faults and "started" become None (unknown), because a stale switch is not a fact.
While the link is unreachable, every suit value is stale too, whatever its own age.

``Store`` also holds what must survive between snapshots: the AlertBook (core/alerts.py) and
the shared view state (``Ui``). Only ``observe`` advances the AlertBook, and only a new
telemetry arrival counts as a sample, so ``preview`` may be called any number of times.
"""

from __future__ import annotations

from typing import Any

from suits.contract import (
    STALE_AFTER_S,
    Alert,
    Eva,
    Level,
    Link,
    LinkStatus,
    Mode,
    Section,
    State,
    Suit,
    SuitValue,
    TssSnapshot,
    Ui,
)
from suits.core import alerts
from suits.core.levels import classify, load_ranges

# The link's severity, decided here so the client never compares statuses itself.
LINK_LEVEL: dict[LinkStatus, Level] = {
    LinkStatus.OK: Level.NOMINAL,
    LinkStatus.STALE: Level.STALE,
    LinkStatus.UNREACHABLE: Level.WARNING,
    LinkStatus.UNASSIGNED: Level.WARNING,
    LinkStatus.BAD_DATA: Level.WARNING,
}


def _fresh(snapshot: TssSnapshot, section: Section) -> bool:
    age = snapshot.ages.get(section)
    return age is not None and age <= STALE_AFTER_S[section]


def suit_values(snapshot: TssSnapshot, ranges: dict[str, Any]) -> dict[str, SuitValue]:
    """Every value named in ranges.json ("ranges" and "unranged"), always all of them."""
    # Telemetry may be younger than its 4 s limit while nothing at all has been heard for 2.5 s
    # (link unreachable). Then the values are not current either, so none of them stays green.
    fresh = _fresh(snapshot, "telemetry") and snapshot.link != LinkStatus.UNREACHABLE
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
    snapshot: TssSnapshot,
    ranges: dict[str, Any],
    mode: Mode,
    seq: int,
    alert_list: tuple[Alert, ...] = (),
    ui: Ui | None = None,
) -> State:
    values = suit_values(snapshot, ranges)
    return State(
        seq=seq,
        t=snapshot.t,
        link=Link(
            tss=snapshot.link, age_s=snapshot.age_s, mode=mode, level=LINK_LEVEL[snapshot.link]
        ),
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
        alerts=alert_list,
        ui=ui or Ui(),
    )


def alert_inputs(state: State, snapshot: TssSnapshot) -> alerts.AlertInputs:
    """What the AlertBook looks at: the levels and facts of ``state``, plus the arrival counter
    and missing names that only the snapshot has."""
    return alerts.AlertInputs(
        t=state.t,
        telemetry_arrival=snapshot.arrivals.get("telemetry"),
        values=state.suit.values,
        faults=state.suit.faults,
        dcu=state.dcu,
        link=state.link.tss,
        eva_started=state.eva.started,
        missing=snapshot.missing,
    )


def content_key(state: State) -> str:
    """What counts as a change: everything except the counters and clocks."""
    return state.model_dump_json(exclude={"seq": True, "t": True, "link": {"age_s"}})


class Store:
    """Holds the ranges, the alert rules, the AlertBook, the shared Ui and the message counter."""

    def __init__(
        self,
        mode: Mode,
        ranges: dict[str, Any] | None = None,
        rules: alerts.Rules | None = None,
    ) -> None:
        self.mode = mode
        self.ranges = ranges if ranges is not None else load_ranges()
        self.rules = rules if rules is not None else alerts.load_rules(self.ranges)
        self.book = alerts.AlertBook()
        self.ui = Ui()
        self.seq = 0

    def _next_book(self, snapshot: TssSnapshot) -> alerts.AlertBook:
        base = build_state(snapshot, self.ranges, self.mode, self.seq + 1)
        return alerts.step(self.book, alert_inputs(base, snapshot), self.rules)

    def observe(self, snapshot: TssSnapshot) -> None:
        """Advance the AlertBook with this snapshot. Calling it twice for one snapshot is
        harmless: only a new telemetry arrival counts as a sample (decision C)."""
        self.book = self._next_book(snapshot)

    def preview(self, snapshot: TssSnapshot) -> State:
        """The State the next send would carry. Changes nothing: not the sequence number, not
        the AlertBook. Its alerts are what ``observe(snapshot)`` would leave in the book."""
        book = self._next_book(snapshot)
        return build_state(
            snapshot, self.ranges, self.mode, self.seq + 1, book.alerts(), self.ui
        )

    def commit(self, state: State) -> State:
        self.seq = state.seq
        return state

    # ---- commands (core/commands.py calls these) ----

    def ack(self, alert_id: str | None) -> str | None:
        """Acknowledge an alert (decision B). Returns the id acknowledged, None if nothing was."""
        self.book, acked = alerts.ack(self.book, alert_id)
        return acked

    def toggle_details(self) -> bool:
        """Open or close the details page. Returns whether it is open now."""
        self.ui = Ui(details_open=not self.ui.details_open)
        return self.ui.details_open
