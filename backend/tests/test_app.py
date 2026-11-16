"""Acceptance 9: the app in sim mode, over a real WebSocket, against the built-in fake TSS."""

import time

import pytest
from fastapi.testclient import TestClient
from suits.app import create_app
from suits.contract import Mode
from suits.settings import Settings, SettingsError


@pytest.fixture
def client():
    with TestClient(create_app(Settings(mode=Mode.SIM))) as c:
        yield c


def receive_until(ws, predicate, timeout: float):
    """Read state messages until predicate(msg) is true. Returns (msg, seconds waited)."""
    start = time.monotonic()
    while True:
        msg = ws.receive_json()
        if predicate(msg):
            return msg, time.monotonic() - start
        if time.monotonic() - start > timeout:
            raise AssertionError(f"no matching state within {timeout} s; last: {msg['link']}")


def o2(msg):
    return msg["suit"]["values"]["oxy_pri_storage"]


def test_ws_sends_state_v2_with_the_fakes_oxygen_value(client):
    fake = client.app.state.runtime.fake_tss
    with client.websocket_connect("/ws") as ws:
        msg, _ = receive_until(ws, lambda m: m["link"]["tss"] == "ok", timeout=5)

    assert msg["type"] == "state" and msg["v"] == 2
    assert msg["link"]["mode"] == "sim"
    assert o2(msg)["value"] == fake.state["telemetry"]["oxy_pri_storage"]
    assert o2(msg)["level"] == "nominal"
    assert msg["dcu"]["oxy"] == "PRI"  # a named position, not a boolean
    assert not isinstance(msg["dcu"]["oxy"], bool)


def test_oxygen_at_15_gives_warning_within_2_s(client):
    fake = client.app.state.runtime.fake_tss
    with client.websocket_connect("/ws") as ws:
        receive_until(ws, lambda m: m["link"]["tss"] == "ok", timeout=5)

        fake.state["telemetry"]["oxy_pri_storage"] = 15
        msg, waited = receive_until(ws, lambda m: o2(m)["level"] == "warning", timeout=2)

    assert waited <= 2
    assert o2(msg)["value"] == 15


def test_flipping_the_switch_reaches_the_client(client):
    fake = client.app.state.runtime.fake_tss
    with client.websocket_connect("/ws") as ws:
        receive_until(ws, lambda m: m["dcu"] is not None, timeout=5)

        fake.state["dcu"]["oxy"] = False

        msg, _ = receive_until(ws, lambda m: m["dcu"] and m["dcu"]["oxy"] == "SEC", timeout=3)
    assert msg["dcu"]["oxy"] == "SEC"


def test_states_keep_coming_once_a_second_with_rising_seq(client):
    with client.websocket_connect("/ws") as ws:
        first = ws.receive_json()
        start = time.monotonic()
        later = [ws.receive_json() for _ in range(3)]

    assert time.monotonic() - start < 3.5
    seqs = [first["seq"], *(m["seq"] for m in later)]
    assert seqs == sorted(seqs) and len(set(seqs)) == 4


def test_health(client):
    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["mode"] == "sim"


@pytest.mark.parametrize(
    "env",
    [
        {"SUITS_MODE": "orbit"},
        {"SUITS_MODE": "live"},  # no TSS_HOST
        {"SUITS_MODE": "replay"},  # no SUITS_RECORDING
        {"SUITS_MODE": "live", "TSS_HOST": "10.0.0.2", "TSS_TEAM": "12"},
    ],
)
def test_bad_settings_are_refused(env):
    with pytest.raises(SettingsError):
        Settings.from_env(env)
