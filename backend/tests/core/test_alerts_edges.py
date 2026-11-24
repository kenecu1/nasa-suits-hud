"""AlertBook edges found in the session-1 reviews: the rules file, link and data alerts,
escalation, unknown inputs, an unknown DCU, and arrivals the publisher did not see one by one."""

import json

import pytest

from suits.contract import SECTIONS, DcuPositions, LinkStatus, Mode, SuitFaults, TssSnapshot
from suits.core import alerts
from suits.core.levels import load_ranges
from suits.core.store import Store
from suits.sim.fake_tss import default_state

DCU = DcuPositions(batt="LOCAL", oxy="PRI", comm="A", fan="PRI", pump="CLOSED", co2="A")
CALM = SuitFaults(fan=False, oxy=False, power=False, scrubber=False)


def snap(arrival: int, link=LinkStatus.OK, dcu=DCU, missing=(), ages=0.1, **values) -> TssSnapshot:
    telemetry = {**default_state()["telemetry"], **values}
    return TssSnapshot(
        t=1000.0 + arrival, link=link, ages={s: ages for s in SECTIONS},
        arrivals={"telemetry": arrival}, missing=missing,
        telemetry={k: v for k, v in telemetry.items() if k not in missing},
        started=True, faults=CALM, dcu=dcu, uia=None,
    )


def run(store: Store, *snapshots: TssSnapshot) -> dict:
    for s in snapshots:
        store.observe(s)
    return {a.id: a for a in store.preview(snapshots[-1]).alerts}


# ---- the rules file ----


def write_rules(tmp_path, change) -> object:
    data = json.loads(alerts.ALERTS_FILE.read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / "alerts.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _drop_link_stale(d):
    del d["link"]["stale"]


@pytest.mark.parametrize("change, problem", [
    (lambda d: d["rules"][0]["values"].append({"value": "warp_drive", "label": "X"}),
     "warp_drive not in ranges.json"),
    (lambda d: d["rules"][0]["values"][0]["by_position"].pop("SEC"), "by_position"),
    (lambda d: d["rules"][0]["values"][0].update(switch="hatch"), "no DCU switch"),
    (lambda d: d["rules"].append({**d["rules"][-1], "id": "link"}), "not allowed or repeated"),
    (lambda d: d["rules"].append({**d["rules"][-1], "id": "temperature2"}),
     "one value belongs to one problem"),
    (lambda d: d["rules"][0].update(fault="gremlins"), "fault"),
    (_drop_link_stale, "no text for stale"),
    (lambda d: d["rules"][0]["values"].append({"label": "X"}), "either value"),
], ids=["unknown-value", "by-position-incomplete", "unknown-switch", "id-clash",
        "value-in-two-rules", "unknown-fault", "link-text-missing", "input-without-value"])
def test_a_bad_rules_file_is_refused_and_says_why(tmp_path, change, problem):
    with pytest.raises(alerts.AlertsError, match=problem):
        alerts.load_rules(load_ranges(), write_rules(tmp_path, change))


def test_duplicate_keys_and_broken_json_are_refused(tmp_path):
    path = tmp_path / "alerts.json"
    path.write_text('{"rules": [], "rules": []}', encoding="utf-8")
    with pytest.raises(alerts.AlertsError, match="duplicate key"):
        alerts.load_rules(load_ranges(), path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(alerts.AlertsError, match="not valid JSON"):
        alerts.load_rules(load_ranges(), path)


def test_every_ranged_value_belongs_to_exactly_one_problem():
    rules = alerts.load_rules(load_ranges())
    watched = [n for r in rules.problems for v in r.values for n in v.names()]

    assert sorted(watched) == sorted(load_ranges()["ranges"])


# ---- link and data alerts ----


def test_unassigned_gives_a_link_warning_and_suit_alerts_keep_working():
    store = Store(Mode.SIM)
    found = run(store, snap(1, link=LinkStatus.UNASSIGNED, heart_rate=170),
                snap(2, link=LinkStatus.UNASSIGNED, heart_rate=170))

    assert found["link"].severity == "warning" and "NOT ASSIGNED" in found["link"].title
    assert "heart_rate" in found  # legacy telemetry needs no team assignment


def test_old_telemetry_while_the_link_is_heard_gives_one_link_caution():
    store = Store(Mode.SIM)
    found = run(store, snap(1, link=LinkStatus.STALE, ages=10.0))

    assert list(found) == ["link"]
    assert found["link"].severity == "caution" and found["link"].title == "SUIT DATA OLD"


def test_a_stale_link_with_fresh_telemetry_raises_nothing():
    # at start-up status and faults take ~7 s to arrive: no alert for that
    store = Store(Mode.SIM)

    assert run(store, snap(1, link=LinkStatus.STALE)) == {}


def test_the_data_alert_clears_as_soon_as_the_names_return():
    store = Store(Mode.SIM)
    assert "data" in run(store, snap(1, link=LinkStatus.BAD_DATA, missing=("heart_rate",)))

    assert run(store, snap(2)) == {}


# ---- escalation and recovery ----


def test_escalation_keeps_id_and_since_and_asks_to_be_seen_again():
    store = Store(Mode.SIM)
    first = run(store, snap(1, heart_rate=155), snap(2, heart_rate=155))["heart_rate"]
    assert first.severity == "caution"
    store.ack("heart_rate")

    found = run(store, snap(3, heart_rate=170), snap(4, heart_rate=170))["heart_rate"]

    assert found.severity == "warning"
    assert found.since == first.since
    assert found.acked is False


def test_a_caution_sample_during_recovery_restarts_the_count():
    store = Store(Mode.SIM)
    run(store, snap(1, heart_rate=170), snap(2, heart_rate=170))
    found = run(store, snap(3), snap(4), snap(5, heart_rate=155), snap(6), snap(7))

    assert "heart_rate" in found  # only 2 nominal in a row since the caution


def test_an_unknown_value_never_counts_toward_clearing():
    store = Store(Mode.SIM)
    run(store, snap(1, heart_rate=170), snap(2, heart_rate=170))

    found = run(store, *(snap(n, heart_rate=None) for n in range(3, 8)))

    assert "heart_rate" in found  # held, not cleared, while the value is unknown


# ---- an unknown DCU position (switch-selected values) ----


def test_with_the_dcu_unknown_a_raised_fan_alert_holds_and_keeps_its_title():
    store = Store(Mode.SIM)
    raised = run(store, snap(1, fan_pri_rpm=20000), snap(2, fan_pri_rpm=20000))["fan"]
    assert raised.title == "FAN PRI 20000 rpm"

    found = run(store, *(snap(n, dcu=None) for n in range(3, 8)))

    assert "fan" in found  # helmet CO2 is nominal, but the fan itself is not watched
    assert found["fan"].title == raised.title


def test_with_the_dcu_unknown_a_known_bad_input_still_raises():
    store = Store(Mode.SIM)

    found = run(store, snap(1, dcu=None, helmet_pressure_co2=0.3),
                snap(2, dcu=None, helmet_pressure_co2=0.3))

    assert found["fan"].title.startswith("HELMET CO2")


# ---- arrivals the publisher saw only at its next heartbeat ----


def test_arrivals_between_two_steps_all_count():
    # unchanged replies wake nobody; the publisher's heartbeat sees arrival 1, then 3
    store = Store(Mode.SIM)

    found = run(store, snap(1, heart_rate=170), snap(3, heart_rate=170))

    assert "heart_rate" in found


def test_three_quiet_arrivals_seen_at_once_clear_an_alert():
    store = Store(Mode.SIM)
    run(store, snap(1, heart_rate=170), snap(2, heart_rate=170))

    assert run(store, snap(5)) == {}
