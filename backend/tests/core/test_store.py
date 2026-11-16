"""TssSnapshot -> State: levels, staleness, unknowns, change detection."""

import pytest
from suits.contract import (
    STALE_AFTER_S,
    DcuPositions,
    Level,
    LinkStatus,
    Mode,
    TssSnapshot,
)
from suits.core.levels import load_ranges
from suits.core.store import Store, build_state, content_key

RANGES = load_ranges()
ALL_NAMES = set(RANGES["ranges"]) | set(RANGES["unranged"])
DCU = DcuPositions(batt="LOCAL", oxy="PRI", comm="A", fan="PRI", pump="CLOSED", co2="A")


def snapshot(telemetry=None, started=True, age=0.5, **overrides) -> TssSnapshot:
    fields = dict(
        t=1000.0,
        link=LinkStatus.OK,
        ages={s: age for s in ("telemetry", "status", "faults", "dcu", "uia")},
        telemetry=telemetry if telemetry is not None else {"oxy_pri_storage": 92.0},
        started=started,
        faults=None,
        dcu=DCU,
        uia=None,
    )
    fields.update(overrides)
    return TssSnapshot(**fields)


def state(snap: TssSnapshot):
    return build_state(snap, RANGES, Mode.SIM, seq=1)


def test_state_has_version_2_and_every_telemetry_name():
    s = state(snapshot())

    assert s.type == "state" and s.v == 2
    assert set(s.suit.values) == ALL_NAMES
    assert len(ALL_NAMES) == 23


@pytest.mark.parametrize(
    ("value", "level"),
    [(92.0, Level.NOMINAL), (25.0, Level.CAUTION), (15.0, Level.WARNING)],
)
def test_primary_oxygen_level(value, level):
    o2 = state(snapshot({"oxy_pri_storage": value})).suit.values["oxy_pri_storage"]

    assert (o2.value, o2.unit, o2.level) == (value, "%", level)


def test_missing_value_is_unknown():
    s = state(snapshot({"oxy_pri_storage": 92.0}))

    assert s.suit.values["heart_rate"].value is None
    assert s.suit.values["heart_rate"].level == Level.UNKNOWN


def test_old_telemetry_is_stale_but_keeps_its_number():
    s = state(snapshot({"oxy_pri_storage": 15.0}, age=max(STALE_AFTER_S.values()) + 0.1))

    assert s.suit.values["oxy_pri_storage"].level == Level.STALE
    assert s.suit.values["oxy_pri_storage"].value == 15.0


def test_old_switches_and_status_become_unknown():
    s = state(snapshot(age=max(STALE_AFTER_S.values()) + 0.1))

    assert s.dcu is None
    assert s.eva.started is None


def test_before_the_eva_starts_nothing_is_flagged():
    s = state(snapshot({"oxy_pri_storage": 0.0}, started=False))

    assert s.suit.values["oxy_pri_storage"].level == Level.NOMINAL


def test_elapsed_time_is_reported_and_has_no_range():
    s = state(snapshot({"eva_elapsed_time": 312.0}))

    assert s.eva.elapsed_s == 312.0
    assert s.suit.values["eva_elapsed_time"].unit == "s"
    assert s.suit.values["eva_elapsed_time"].level == Level.NOMINAL


def test_dcu_is_named_positions():
    s = state(snapshot())

    assert s.model_dump()["dcu"]["oxy"] == "PRI"


def test_content_key_ignores_seq_time_and_age():
    a = build_state(snapshot(age=0.1), RANGES, Mode.SIM, seq=1)
    b = build_state(snapshot(age=0.9, t=2000.0), RANGES, Mode.SIM, seq=2)
    c = build_state(snapshot({"oxy_pri_storage": 15.0}), RANGES, Mode.SIM, seq=3)

    assert content_key(a) == content_key(b)
    assert content_key(a) != content_key(c)


def test_store_numbers_only_committed_states():
    store = Store(Mode.SIM, RANGES)

    first = store.preview(snapshot())
    again = store.preview(snapshot())
    store.commit(again)

    assert first.seq == again.seq == 1
    assert store.preview(snapshot()).seq == 2


def test_a_stale_not_started_does_not_silence_alarms():
    # status said "not started" long ago and has gone quiet, while telemetry is fresh
    ages = {"telemetry": 0.5, "status": STALE_AFTER_S["status"] + 1, "faults": 0.5,
            "dcu": 0.5, "uia": 0.5}
    s = state(snapshot({"oxy_pri_storage": 15.0}, started=False, ages=ages))

    assert s.suit.values["oxy_pri_storage"].level == Level.WARNING
    assert s.eva.started is None


def test_a_fresh_not_started_does_silence_alarms():
    s = state(snapshot({"oxy_pri_storage": 15.0}, started=False))

    assert s.suit.values["oxy_pri_storage"].level == Level.NOMINAL
