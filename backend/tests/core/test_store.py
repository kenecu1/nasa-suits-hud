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
from suits.core.levels import RANGES_FILE as RANGES_PATH
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
    s = state(snapshot({"eva_elapsed_time": 312.0}, elapsed_s=312.0))

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


def test_elapsed_time_comes_from_the_snapshot_not_a_tss_name():
    s = state(snapshot({"oxy_pri_storage": 92.0}, elapsed_s=312.0))

    assert s.eva.elapsed_s == 312.0


def test_elapsed_time_is_unknown_when_telemetry_is_stale():
    s = state(snapshot({}, elapsed_s=312.0, age=max(STALE_AFTER_S.values()) + 0.1))

    assert s.eva.elapsed_s is None


def test_values_go_stale_as_soon_as_the_link_is_unreachable():
    # telemetry is 3 s old (fresh by its own 4 s limit) but nothing was heard for 2.5 s
    s = state(snapshot({"oxy_pri_storage": 92.0}, age=3.0, link=LinkStatus.UNREACHABLE))

    assert s.suit.values["oxy_pri_storage"].level == Level.STALE
    assert s.suit.values["oxy_pri_storage"].value == 92.0


# ---- M2: link level, and preview never changes the AlertBook ----


@pytest.mark.parametrize("link, level", [
    (LinkStatus.OK, "nominal"), (LinkStatus.STALE, "stale"), (LinkStatus.UNREACHABLE, "warning"),
    (LinkStatus.UNASSIGNED, "warning"), (LinkStatus.BAD_DATA, "warning"),
])
def test_the_backend_decides_the_links_level(link, level):
    assert state(snapshot(link=link)).link.level == level


def off_nominal(arrival: int) -> TssSnapshot:
    return snapshot(telemetry={"heart_rate": 170.0}, arrivals={"telemetry": arrival})


def test_preview_does_not_advance_the_alertbook_however_often_it_runs():
    store = Store(Mode.SIM)
    store.observe(off_nominal(1))
    book = store.book

    for arrival in (2, 3, 4):
        assert [a.id for a in store.preview(off_nominal(arrival)).alerts] == ["heart_rate"]

    assert store.book is book  # unchanged: only observe moves it


def test_observe_counts_one_arrival_once():
    store = Store(Mode.SIM)
    store.observe(off_nominal(1))
    store.observe(off_nominal(1))
    store.observe(off_nominal(1))

    assert store.preview(off_nominal(1)).alerts == ()  # 1 sample, not 3
    store.observe(off_nominal(2))
    assert [a.id for a in store.preview(off_nominal(2)).alerts] == ["heart_rate"]


def test_clearing_is_counted_even_when_no_state_is_sent_in_between():
    # The publisher sends only on change or heartbeat; constant nominal values change nothing
    # after the first, but each arrival must still count toward the 3 that clear an alert.
    store = Store(Mode.SIM)
    for arrival in (1, 2):
        store.observe(off_nominal(arrival))
    calm = {"heart_rate": 92.0}
    for arrival in (3, 4, 5):
        store.observe(snapshot(telemetry=calm, arrivals={"telemetry": arrival}))

    assert store.preview(snapshot(telemetry=calm, arrivals={"telemetry": 5})).alerts == ()


# The inactive fan (approved by Vlad in M2 session 2): only the active fan spins, so the one
# the DCU FAN switch does not select reads 0 rpm. It is "off", not a warning.
@pytest.mark.parametrize(
    ("position", "active", "inactive"),
    [("PRI", "fan_pri_rpm", "fan_sec_rpm"), ("SEC", "fan_sec_rpm", "fan_pri_rpm")],
)
def test_the_fan_the_dcu_does_not_select_is_off(position, active, inactive):
    dcu = DCU.model_copy(update={"fan": position})
    s = state(snapshot({active: 30000.0, inactive: 0.0}, dcu=dcu))

    assert s.suit.values[active].level == Level.NOMINAL
    assert s.suit.values[inactive].level == Level.OFF
    assert s.suit.values[inactive].value == 0.0


def test_the_active_fan_is_still_classified_when_it_fails():
    s = state(snapshot({"fan_pri_rpm": 21500.0, "fan_sec_rpm": 0.0}))

    assert s.suit.values["fan_pri_rpm"].level == Level.WARNING
    assert s.suit.values["fan_sec_rpm"].level == Level.OFF


def test_no_fan_is_off_while_the_dcu_position_is_unknown():
    ages = {s: 0.5 for s in ("telemetry", "status", "faults", "uia")}
    ages["dcu"] = STALE_AFTER_S["dcu"] + 0.1
    for dcu_overrides in ({"dcu": None}, {"ages": ages}):
        s = state(snapshot({"fan_pri_rpm": 30000.0, "fan_sec_rpm": 0.0}, **dcu_overrides))

        assert s.suit.values["fan_pri_rpm"].level == Level.NOMINAL
        assert s.suit.values["fan_sec_rpm"].level == Level.WARNING


def test_stale_and_unknown_win_over_off():
    old = state(snapshot({"fan_sec_rpm": 0.0}, age=STALE_AFTER_S["telemetry"] + 0.1,
                         ages={"telemetry": STALE_AFTER_S["telemetry"] + 0.1, "status": 0.5,
                               "faults": 0.5, "dcu": 0.5, "uia": 0.5}))
    missing = state(snapshot({"fan_pri_rpm": 30000.0}))

    assert old.suit.values["fan_sec_rpm"].level == Level.STALE
    assert missing.suit.values["fan_sec_rpm"].level == Level.UNKNOWN


def test_no_scrubber_or_other_value_is_ever_off():
    telemetry = {name: 0.0 for name in ALL_NAMES}
    s = state(snapshot(telemetry))

    off = {name for name, v in s.suit.values.items() if v.level == Level.OFF}
    assert off == {"fan_sec_rpm"}


def test_an_off_fan_raises_no_alert():
    store = Store(Mode.SIM)
    for arrival in range(1, 6):
        snap = snapshot({"fan_pri_rpm": 30000.0, "fan_sec_rpm": 0.0}, arrivals={"telemetry": arrival})
        store.observe(snap)
        s = store.preview(snap)

    assert s.suit.values["fan_sec_rpm"].level == Level.OFF
    assert s.alerts == ()


def test_ranges_refuse_an_active_when_position_the_dcu_does_not_have(tmp_path):
    import json

    from suits.core.levels import RangesError

    data = json.loads((RANGES_PATH).read_text(encoding="utf-8"))
    data["ranges"]["fan_pri_rpm"]["active_when"] = {"dcu": "fan", "position": "A"}
    bad = tmp_path / "ranges.json"
    bad.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RangesError, match="no position 'A'"):
        load_ranges(bad)


def test_the_active_fan_reading_zero_is_a_warning_not_off():
    # The real failure: the selected fan stops. It must never be mistaken for a switched-off one.
    s = state(snapshot({"fan_pri_rpm": 0.0, "fan_sec_rpm": 0.0}))

    assert s.suit.values["fan_pri_rpm"].level == Level.WARNING
    assert s.suit.values["fan_sec_rpm"].level == Level.OFF
