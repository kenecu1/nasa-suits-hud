"""sim/dynamics.py and sim/scenarios.py, and acceptance 5: fan_failure at high speed through the
whole backend (fake TSS over UDP -> adapter -> store and AlertBook -> /ws)."""

import time

import pytest
from fastapi.testclient import TestClient

from suits.app import create_app
from suits.contract import Mode
from suits.settings import Settings
from suits.sim import scenarios
from suits.sim.dynamics import FAN_RPM, Dynamics
from suits.sim.fake_tss import FakeTss, default_state
from suits.sim.scenarios import ScenarioError, SimDriver, load_scenario

# ---- dynamics: NASA's fault rules ----


def test_only_the_active_fan_spins():
    state = default_state()
    dynamics = Dynamics(state)

    dynamics.tick(0.1)
    assert (state["telemetry"]["fan_pri_rpm"], state["telemetry"]["fan_sec_rpm"]) == (FAN_RPM, 0)

    state["dcu"]["fan"] = False
    dynamics.tick(0.1)
    assert (state["telemetry"]["fan_pri_rpm"], state["telemetry"]["fan_sec_rpm"]) == (0, FAN_RPM)


def test_a_fan_fault_winds_the_primary_down_and_switching_to_sec_fixes_it():
    state = default_state()
    dynamics = Dynamics(state)
    helmet = state["telemetry"]["helmet_pressure_co2"]
    dynamics.set_fault("fan")

    dynamics.tick(2.0)
    assert state["telemetry"]["fan_pri_rpm"] < 29000  # below the range: warning
    assert state["telemetry"]["helmet_pressure_co2"] > helmet
    assert state["error"]["fan_error"] is True

    state["dcu"]["fan"] = False  # DCU FAN to SEC
    for _ in range(30):
        dynamics.tick(0.5)
    assert state["telemetry"]["fan_sec_rpm"] == FAN_RPM
    assert state["error"]["fan_error"] is False
    assert state["telemetry"]["helmet_pressure_co2"] == pytest.approx(helmet, abs=1e-3)


def test_an_oxygen_fault_on_the_primary_tank_and_its_fix():
    state = default_state()
    dynamics = Dynamics(state)
    dynamics.set_fault("oxy")

    dynamics.tick(20.0)
    assert state["telemetry"]["suit_pressure_oxy"] < 3.5
    assert state["error"]["oxy_error"] is True

    state["dcu"]["oxy"] = False  # DCU OXY to SEC
    dynamics.tick(0.1)
    assert state["error"]["oxy_error"] is False


def test_a_scrubber_fault_sets_the_flag_above_60_percent_and_flipping_clears_it():
    state = default_state()
    dynamics = Dynamics(state)
    dynamics.set_fault("scrubber")

    dynamics.tick(20.0)
    assert state["telemetry"]["scrubber_a_co2_storage"] > 60
    assert state["error"]["scrubber_error"] is True

    dynamics.set_fault("scrubber", False)
    state["dcu"]["co2"] = False  # flip DCU CO2 to B
    dynamics.tick(0.1)
    assert state["error"]["scrubber_error"] is False


def test_a_power_fault_drains_the_primary_battery_below_20_percent():
    state = default_state()
    dynamics = Dynamics(state)
    dynamics.set_fault("power")

    dynamics.tick(40.0)

    assert state["telemetry"]["primary_battery_level"] < 20
    assert state["error"]["power_error"] is True


def test_values_set_by_hand_are_left_alone():
    state = default_state()
    dynamics = Dynamics(state)
    state["telemetry"]["suit_pressure_oxy"] = 3.0  # a test or scenario set it

    dynamics.tick(5.0)

    assert state["telemetry"]["suit_pressure_oxy"] == 3.0


def test_an_unknown_fault_is_refused():
    with pytest.raises(ValueError, match="unknown fault"):
        Dynamics(default_state()).set_fault("gremlins")  # type: ignore[arg-type]


# ---- scenario files and the player ----


@pytest.mark.parametrize("name", ["fan_failure", "o2_leak", "link_loss", "eva_not_started",
                                  "heart_rate_high"])
def test_every_scenario_file_loads(name):
    assert load_scenario(name).steps


def test_scenarios_folder_lists_the_three_from_the_spec():
    assert {"fan_failure", "o2_leak", "link_loss"} <= set(scenarios.available())


def test_an_unknown_scenario_names_the_known_ones():
    with pytest.raises(ScenarioError, match="fan_failure"):
        load_scenario("meteor_strike")


@pytest.mark.parametrize("text, problem", [
    ("steps: []", "steps"),
    ("steps:\n  - at: 1\n", "needs fault"),
    ("steps:\n  - at: -1\n    fault: fan\n", "at"),
    ("steps:\n  - at: 1\n    fault: gremlins\n", "fault"),
    ("steps:\n  - at: 1\n    set: {heart_rate: 3}\n", "bad path"),
    ("- just a list", "mapping"),
    ("steps: [", "cannot read"),
])
def test_a_bad_scenario_file_says_what_is_wrong(tmp_path, text, problem):
    path = tmp_path / "bad.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ScenarioError, match=problem):
        load_scenario("bad", path)


def test_the_player_applies_steps_when_their_time_comes():
    fake = FakeTss()
    driver = SimDriver(fake, load_scenario("link_loss"), speed=10)

    driver.advance(7.9)
    assert fake.silent is False
    driver.advance(0.2)
    assert fake.silent is True
    driver.advance(8.0)
    assert fake.silent is False and driver.finished


def test_set_steps_change_the_fakes_state():
    fake = FakeTss()
    driver = SimDriver(fake, load_scenario("eva_not_started"))

    driver.advance(0.0)

    assert fake.state["status"]["started"] is False


# ---- acceptance 5: fan_failure at high speed, through the whole backend ----


def receive_until(ws, predicate, timeout: float):
    start = time.monotonic()
    while True:
        msg = ws.receive_json()
        if predicate(msg):
            return msg
        if time.monotonic() - start > timeout:
            raise AssertionError(f"no matching state within {timeout} s; alerts: {msg['alerts']}")


def fan_alert(msg):
    return next((a for a in msg["alerts"] if a["id"] == "fan"), None)


def test_fan_failure_raises_a_fan_warning_that_clears_after_dcu_fan_to_sec():
    settings = Settings(mode=Mode.SIM, scenario="fan_failure", scenario_speed=20)
    with TestClient(create_app(settings)) as client:
        runtime = client.app.state.runtime
        with client.websocket_connect("/ws") as ws:
            # wait for the values' part: the title names the primary fan's reading
            msg = receive_until(
                ws, lambda m: (fan_alert(m) or {}).get("title", "").startswith("FAN PRI"),
                timeout=10)
            alert = fan_alert(msg)
            assert alert["severity"] == "warning"
            assert alert["action"] == "DCU FAN to SEC, return to lander"
            assert alert["acked"] is False
            assert msg["suit"]["values"]["fan_pri_rpm"]["level"] == "warning"
            assert msg["alerts"][0]["id"] == "fan"  # the only alert, so on top

            runtime.fake_tss.state["dcu"]["fan"] = False  # the wearer: DCU FAN to SEC
            msg = receive_until(ws, lambda m: fan_alert(m) is None, timeout=15)

    assert msg["dcu"]["fan"] == "SEC"
    assert msg["suit"]["values"]["fan_sec_rpm"]["level"] == "nominal"
    assert msg["suit"]["values"]["fan_sec_rpm"]["value"] == FAN_RPM


def test_link_loss_shows_one_link_alert_and_every_value_stale_then_recovers():
    settings = Settings(mode=Mode.SIM, scenario="link_loss", scenario_speed=2)
    with TestClient(create_app(settings)) as client:
        client.app.state.runtime.sim.dynamics.set_fault("fan")  # a suit alert to suppress
        with client.websocket_connect("/ws") as ws:
            receive_until(ws, lambda m: m["link"]["tss"] == "ok", timeout=5)
            lost = receive_until(ws, lambda m: m["link"]["tss"] == "unreachable", timeout=8)
            back = receive_until(ws, lambda m: m["link"]["tss"] != "unreachable", timeout=10)

    assert [(a["id"], a["severity"]) for a in lost["alerts"]] == [("link", "warning")]
    assert lost["link"]["level"] == "warning"
    assert {v["level"] for v in lost["suit"]["values"].values()} == {"stale"}
    assert all(a["id"] != "link" or a["severity"] != "warning" for a in back["alerts"])
