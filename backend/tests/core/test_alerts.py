"""M2 acceptance 2-4: alerts from levels, fault flags and link status.

Samples go through the real pipeline (Store.observe, then Store.preview(...).alerts), so levels
come from data/ranges.json and the actions from data/alerts.json. One sample is one new
telemetry arrival; a sample is a dict of overrides: a telemetry name changes that value, any
other key (link, ages, started, faults, dcu, missing) changes that snapshot field.
"""

import pytest

from suits.contract import (
    SECTIONS,
    Alert,
    DcuPositions,
    LinkStatus,
    Mode,
    Severity,
    SuitFaults,
    TssSnapshot,
)
from suits.core import alerts
from suits.core.levels import load_ranges
from suits.core.store import Store

NOMINAL = {
    "primary_battery_level": 80.0, "secondary_battery_level": 80.0,
    "oxy_pri_storage": 80.0, "oxy_sec_storage": 80.0,
    "oxy_pri_pressure": 2000.0, "oxy_sec_pressure": 2000.0, "coolant_storage": 90.0,
    "heart_rate": 100.0, "oxy_consumption": 0.1, "co2_production": 0.1,
    "suit_pressure_oxy": 3.8, "suit_pressure_co2": 0.02, "suit_pressure_other": 0.1,
    "suit_pressure_total": 4.0, "helmet_pressure_co2": 0.05,
    "fan_pri_rpm": 30000.0, "fan_sec_rpm": 30000.0,
    "scrubber_a_co2_storage": 20.0, "scrubber_b_co2_storage": 20.0,
    "temperature": 21.0, "coolant_liquid_pressure": 400.0, "coolant_gas_pressure": 300.0,
    "eva_elapsed_time": 100.0,
}
NO_FAULTS = SuitFaults(fan=False, oxy=False, power=False, scrubber=False)
DCU = DcuPositions(batt="LOCAL", oxy="PRI", comm="A", fan="PRI", pump="CLOSED", co2="A")

FAN = "DCU FAN to SEC, return to lander"
OXY = "DCU OXY to SEC, return to lander"
CO2 = "Flip DCU CO2"
BATTERY = "Switch battery"
SLOW = "Slow down"
GENERIC = "Check details, report to LMCC"


def faults(**on: bool) -> SuitFaults:
    return NO_FAULTS.model_copy(update=on)


def snapshot(n: int, **overrides) -> TssSnapshot:
    fields = dict(
        t=1000.0 + 1.5 * n, link=LinkStatus.OK, ages={s: 0.1 for s in SECTIONS},
        arrivals={"telemetry": n}, missing=(), started=True, faults=NO_FAULTS, dcu=DCU, uia=None,
    )
    telemetry = dict(NOMINAL)
    for key, value in overrides.items():
        if key in NOMINAL:
            telemetry[key] = value
        elif key in fields:
            fields[key] = value
        else:
            raise KeyError(key)
    telemetry = {k: v for k, v in telemetry.items() if v is not None}  # None = not sent
    return TssSnapshot(telemetry=telemetry, **fields)


def feed(store: Store, samples: list[dict]) -> tuple[Alert, ...]:
    """Feed one new telemetry arrival per sample; return the alerts after the last."""
    shown: tuple[Alert, ...] = ()
    for sample in samples:
        snap = snapshot((store.book.telemetry_seen or 0) + 1, **sample)
        store.observe(snap)
        shown = store.preview(snap).alerts
    return shown


def by_id(shown: tuple[Alert, ...]) -> dict[str, Alert]:
    return {a.id: a for a in shown}


def ids(shown: tuple[Alert, ...]) -> list[str]:
    return [a.id for a in shown]


@pytest.fixture
def store() -> Store:
    return Store(Mode.SIM)


# ---- acceptance 2: hysteresis and levels ----

LEVEL_CASES = [
    ({"heart_rate": 170.0}, "heart_rate", Severity.WARNING, SLOW),
    ({"heart_rate": 155.0}, "heart_rate", Severity.CAUTION, SLOW),
    ({"heart_rate": 40.0}, "heart_rate", Severity.WARNING, SLOW),
    ({"temperature": 40.0}, "temperature", Severity.WARNING, SLOW),
    ({"suit_pressure_oxy": 3.0}, "oxygen", Severity.WARNING, OXY),
    ({"suit_pressure_co2": 0.3}, "co2", Severity.WARNING, CO2),
    ({"scrubber_a_co2_storage": 70.0}, "co2", Severity.WARNING, CO2),
    ({"fan_pri_rpm": 21500.0}, "fan", Severity.WARNING, FAN),
    ({"primary_battery_level": 10.0}, "battery", Severity.WARNING, BATTERY),
    ({"secondary_battery_level": 10.0}, "battery", Severity.WARNING, BATTERY),
    ({"oxy_pri_storage": 10.0}, "value.oxy_pri_storage", Severity.WARNING, GENERIC),
    ({"oxy_sec_pressure": 100.0}, "value.oxy_sec_pressure", Severity.WARNING, GENERIC),
    ({"coolant_storage": 50.0}, "value.coolant_storage", Severity.WARNING, GENERIC),
    ({"coolant_liquid_pressure": 900.0}, "value.coolant_liquid_pressure", Severity.WARNING, GENERIC),
    ({"suit_pressure_total": 6.0}, "value.suit_pressure_total", Severity.WARNING, GENERIC),
    ({"co2_production": 0.5}, "value.co2_production", Severity.WARNING, GENERIC),
]
LEVEL_IDS = [case[1] + ("_caution" if case[2] == Severity.CAUTION else "") for case in LEVEL_CASES]
LEVEL_IDS[2] = "heart_rate_low"


@pytest.mark.parametrize(("sample", "alert_id", "severity", "action"), LEVEL_CASES, ids=LEVEL_IDS)
def test_two_samples_off_nominal_raise_one_alert_with_its_action(
    store, sample, alert_id, severity, action
):
    assert feed(store, [sample]) == ()
    shown = feed(store, [sample])
    assert ids(shown) == [alert_id]
    assert shown[0].severity == severity
    assert shown[0].action == action
    assert shown[0].acked is False


def test_nominal_values_raise_nothing(store):
    assert feed(store, [{}] * 5) == ()


def test_the_same_snapshot_fed_twice_does_not_raise(store):
    snap = snapshot(1, heart_rate=170.0)
    store.observe(snap)
    store.observe(snap)
    assert store.preview(snap).alerts == ()
    assert ids(feed(store, [{"heart_rate": 170.0}])) == ["heart_rate"]


def test_a_step_without_a_telemetry_arrival_never_counts():
    rules = alerts.load_rules(load_ranges())
    book = alerts.AlertBook()
    bad = Store(Mode.SIM).preview(snapshot(1, heart_rate=170.0)).suit.values
    inputs = alerts.AlertInputs(
        t=1.0, telemetry_arrival=None, values=bad, faults=NO_FAULTS, dcu=DCU,
        link=LinkStatus.OK, eva_started=True,
    )
    for _ in range(5):
        book = alerts.step(book, inputs, rules)
    assert book.alerts() == ()


def test_a_nominal_sample_between_two_off_samples_starts_the_count_again(store):
    assert feed(store, [{"heart_rate": 170.0}, {}, {"heart_rate": 170.0}]) == ()


def test_an_alert_clears_only_after_three_nominal_samples(store):
    feed(store, [{"heart_rate": 170.0}] * 2)
    assert ids(feed(store, [{}] * 2)) == ["heart_rate"]
    assert feed(store, [{}]) == ()


def test_an_off_sample_during_recovery_restarts_the_clearing(store):
    feed(store, [{"heart_rate": 170.0}] * 2)
    assert ids(feed(store, [{}, {}, {"heart_rate": 170.0}, {}, {}])) == ["heart_rate"]


def test_severity_is_the_worst_of_the_rules_inputs(store):
    shown = feed(store, [{"primary_battery_level": 25.0, "secondary_battery_level": 10.0}] * 2)
    assert by_id(shown)["battery"].severity == Severity.WARNING


def test_a_caution_becomes_a_warning_after_two_warning_samples_and_must_be_seen_again(store):
    assert by_id(feed(store, [{"heart_rate": 155.0}] * 2))["heart_rate"].severity == (
        Severity.CAUTION
    )
    store.ack("heart_rate")
    one = by_id(feed(store, [{"heart_rate": 170.0}]))["heart_rate"]
    assert (one.severity, one.acked) == (Severity.CAUTION, True)
    two = by_id(feed(store, [{"heart_rate": 170.0}]))["heart_rate"]
    assert (two.severity, two.acked) == (Severity.WARNING, False)


def test_a_warning_drops_to_caution_after_three_samples_without_warning(store):
    feed(store, [{"heart_rate": 170.0}] * 2)
    assert by_id(feed(store, [{"heart_rate": 155.0}] * 2))["heart_rate"].severity == (
        Severity.WARNING
    )
    assert by_id(feed(store, [{"heart_rate": 155.0}]))["heart_rate"].severity == Severity.CAUTION


# ---- acceptance 3: fault flags, switches, stable ids ----

FAULT_CASES = [
    ("fan", "fan", FAN),
    ("oxy", "oxygen", OXY),
    ("power", "battery", BATTERY),
    ("scrubber", "co2", CO2),
]


@pytest.mark.parametrize(("flag", "alert_id", "action"), FAULT_CASES, ids=[c[0] for c in FAULT_CASES])
def test_a_fault_flag_raises_a_warning_at_once_and_clears_at_once(store, flag, alert_id, action):
    shown = feed(store, [{"faults": faults(**{flag: True})}])
    assert ids(shown) == [alert_id]
    assert shown[0].severity == Severity.WARNING
    assert shown[0].action == action
    assert feed(store, [{}]) == ()


def test_the_active_fan_is_the_one_the_dcu_switch_selects(store):
    sec = DCU.model_copy(update={"fan": "SEC"})
    assert feed(store, [{"dcu": sec, "fan_pri_rpm": 0.0}] * 3) == ()
    assert ids(feed(store, [{"dcu": sec, "fan_sec_rpm": 0.0}] * 2)) == ["fan"]


def test_the_inactive_scrubber_raises_nothing_until_it_is_selected(store):
    assert feed(store, [{"scrubber_b_co2_storage": 70.0}] * 3) == ()
    to_b = DCU.model_copy(update={"co2": "B"})
    assert ids(feed(store, [{"dcu": to_b, "scrubber_b_co2_storage": 70.0}] * 2)) == ["co2"]


def test_without_dcu_positions_the_switch_selected_values_are_skipped(store):
    assert feed(store, [{"dcu": None, "fan_pri_rpm": 0.0, "scrubber_a_co2_storage": 90.0}] * 3) == ()


def test_alert_ids_and_since_stay_the_same_while_the_alert_is_active(store):
    first = by_id(feed(store, [{"heart_rate": 155.0}] * 2))["heart_rate"]
    later = by_id(feed(store, [{"heart_rate": 155.0}, {"heart_rate": 170.0}] * 2))["heart_rate"]
    assert later.id == first.id
    assert later.since == first.since


# ---- acknowledging and sorting ----


def test_ack_by_id_acknowledges_only_that_alert(store):
    feed(store, [{"heart_rate": 170.0, "temperature": 40.0}] * 2)
    assert store.ack("temperature") == "temperature"
    shown = by_id(store.book.alerts())
    assert (shown["temperature"].acked, shown["heart_rate"].acked) == (True, False)


def test_ack_without_an_id_acknowledges_the_top_unacknowledged_alert(store):
    feed(store, [{"heart_rate": 155.0, "faults": faults(fan=True)}] * 2)
    assert store.ack(None) == "fan"
    assert store.ack(None) == "heart_rate"
    assert store.ack(None) is None


def test_ack_of_an_unknown_id_changes_nothing(store):
    feed(store, [{"heart_rate": 170.0}] * 2)
    before = store.book
    assert store.ack("no_such_alert") is None
    assert store.book == before


def test_ack_does_not_change_the_old_book():
    rules = alerts.load_rules(load_ranges())
    store = Store(Mode.SIM, rules=rules)
    feed(store, [{"heart_rate": 170.0}] * 2)
    old = store.book
    new, acked = alerts.ack(old, "heart_rate")
    assert acked == "heart_rate"
    assert old.active["heart_rate"].acked is False
    assert new.active["heart_rate"].acked is True


def test_an_acked_alert_stays_acked_and_listed_until_it_clears(store):
    feed(store, [{"heart_rate": 170.0}] * 2)
    store.ack("heart_rate")
    shown = feed(store, [{"heart_rate": 170.0}] * 3 + [{}] * 2)
    assert [(a.id, a.acked) for a in shown] == [("heart_rate", True)]


def test_an_alert_that_clears_and_comes_back_is_new_and_unacked(store):
    old = by_id(feed(store, [{"heart_rate": 170.0}] * 2))["heart_rate"]
    store.ack("heart_rate")
    assert feed(store, [{}] * 3) == ()
    new = by_id(feed(store, [{"heart_rate": 170.0}] * 2))["heart_rate"]
    assert new.acked is False
    assert new.since > old.since


def test_alerts_sort_unacked_first_then_warning_then_newest(store):
    feed(store, [{"heart_rate": 155.0}] * 2)
    feed(store, [{"heart_rate": 155.0, "temperature": 31.0}] * 2)
    both = {"heart_rate": 155.0, "temperature": 31.0, "faults": faults(oxy=True)}
    assert ids(feed(store, [both])) == ["oxygen", "temperature", "heart_rate"]
    store.ack("oxygen")
    assert ids(store.book.alerts()) == ["temperature", "heart_rate", "oxygen"]
    store.ack("temperature")
    assert ids(store.book.alerts()) == ["heart_rate", "oxygen", "temperature"]


# ---- acceptance 4: link, EVA start, stale values, missing names ----


def test_an_unreachable_link_is_the_only_alert_even_with_faults_and_off_values(store):
    feed(store, [{"heart_rate": 170.0}] * 2)
    lost = {"link": LinkStatus.UNREACHABLE, "faults": faults(fan=True, oxy=True, power=True),
            "heart_rate": 170.0, "suit_pressure_oxy": 3.0}
    shown = feed(store, [lost] * 3)
    assert ids(shown) == ["link"]
    assert shown[0].severity == Severity.WARNING


def test_after_the_link_returns_a_problem_needs_two_fresh_samples_and_is_unacked(store):
    feed(store, [{"heart_rate": 170.0}] * 2)
    store.ack("heart_rate")
    feed(store, [{"link": LinkStatus.UNREACHABLE, "heart_rate": 170.0}] * 2)
    assert feed(store, [{"heart_rate": 170.0}]) == ()
    shown = by_id(feed(store, [{"heart_rate": 170.0}]))
    assert ids(tuple(shown.values())) == ["heart_rate"]
    assert shown["heart_rate"].acked is False


def test_before_the_eva_starts_there_are_no_suit_alerts(store):
    off = {"started": False, "faults": faults(fan=True), "heart_rate": 170.0}
    assert feed(store, [off] * 4) == ()


def test_the_eva_starting_turns_the_alerts_on(store):
    off = {"started": False, "faults": faults(fan=True), "heart_rate": 170.0}
    feed(store, [off] * 2)
    assert ids(feed(store, [{**off, "started": True}])) == ["fan"]


@pytest.mark.parametrize(
    "unknown",
    [{"started": None}, {"started": False, "ages": {**{s: 0.1 for s in SECTIONS}, "status": 30.0}}],
    ids=["no status yet", "status too old"],
)
def test_an_unknown_eva_start_counts_as_started(store, unknown):
    shown = feed(store, [{**unknown, "faults": faults(fan=True), "heart_rate": 170.0}] * 2)
    assert sorted(ids(shown)) == ["fan", "heart_rate"]


def test_a_stale_value_clears_its_alert(store):
    feed(store, [{"heart_rate": 170.0}] * 2)
    old = {"heart_rate": 170.0, "link": LinkStatus.STALE,
           "ages": {**{s: 0.1 for s in SECTIONS}, "telemetry": 5.0}}
    assert "heart_rate" not in ids(feed(store, [old]))


def test_a_stale_value_resets_the_count_of_its_problem(store):
    old = {"heart_rate": 170.0, "link": LinkStatus.STALE,
           "ages": {**{s: 0.1 for s in SECTIONS}, "telemetry": 5.0}}
    feed(store, [{"heart_rate": 170.0}, old])
    assert "heart_rate" not in ids(feed(store, [{"heart_rate": 170.0}]))
    assert "heart_rate" in ids(feed(store, [{"heart_rate": 170.0}]))


def test_a_missing_field_is_one_data_caution_and_no_link_alert(store):
    gone = {"oxy_pri_storage": None, "missing": ("oxy_pri_storage",), "link": LinkStatus.BAD_DATA}
    shown = feed(store, [gone] * 3)
    assert ids(shown) == ["data"]
    assert shown[0].severity == Severity.CAUTION
    assert "1 FIELD MISSING" in shown[0].title
    assert "oxy_pri_storage" in shown[0].action


def test_several_missing_fields_are_counted_and_all_named(store):
    names = ("oxy_pri_storage", "oxy_sec_storage")
    gone = {"oxy_pri_storage": None, "oxy_sec_storage": None, "missing": names,
            "link": LinkStatus.BAD_DATA}
    shown = feed(store, [gone])
    assert "2 FIELDS MISSING" in shown[0].title
    assert all(name in shown[0].action for name in names)


def test_bad_data_without_a_missing_name_is_a_link_warning(store):
    shown = feed(store, [{"link": LinkStatus.BAD_DATA}])
    assert ids(shown) == ["link"]
    assert shown[0].severity == Severity.WARNING
