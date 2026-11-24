"""Acceptance 9: the app in sim mode, over a real WebSocket, against the built-in fake TSS."""

import time
from pathlib import Path

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


def test_health_reports_mode_link_and_clients(client):
    with client.websocket_connect("/ws") as ws:
        receive_until(ws, lambda m: m["link"]["tss"] == "ok", timeout=5)
        body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["mode"] == "sim"
    assert body["tss"] == "ok"
    assert body["clients"] == 1
    assert body["seq"] >= 1
    assert body["dead_tasks"] == []


def test_a_closed_client_is_forgotten_at_once(client):
    publisher = client.app.state.runtime.publisher
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        assert publisher.subscriber_count == 1

    deadline = time.monotonic() + 0.5  # well under one heartbeat
    while publisher.subscriber_count and time.monotonic() < deadline:
        time.sleep(0.02)
    assert publisher.subscriber_count == 0


def test_replay_mode_serves_the_recording():
    recording = Path(__file__).parent / "fixtures" / "captured-tss.jsonl"
    settings = Settings(mode=Mode.REPLAY, recording=recording, replay_speed=4.0)
    with TestClient(create_app(settings)) as c, c.websocket_connect("/ws") as ws:
        msg, _ = receive_until(ws, lambda m: bool(m["dcu"]) and m["dcu"]["oxy"] == "PRI", 5)

    assert msg["link"]["mode"] == "replay"
    assert o2(msg)["unit"] == "%"


def test_a_failed_start_leaves_nothing_open(monkeypatch):
    import suits.runtime as runtime_module

    started: list = []

    class TrackedFake(runtime_module.FakeTss):
        async def start(self):
            await super().start()
            started.append(self)

    def broken_client(*args, **kwargs):
        raise OSError("no network")

    monkeypatch.setattr(runtime_module, "FakeTss", TrackedFake)
    monkeypatch.setattr(runtime_module, "TssClient", broken_client)

    with pytest.raises(OSError), TestClient(create_app(Settings(mode=Mode.SIM))):
        pass

    assert len(started) == 1
    transport = started[0]._sub.transport
    assert transport is None or transport.is_closing()


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


def test_health_is_degraded_and_names_a_task_that_died(client):
    from suits.tasks import spawn

    runtime = client.app.state.runtime

    async def boom():
        raise RuntimeError("boom")

    def start_boom():
        runtime.tasks.append(spawn(boom(), "boom"))

    client.portal.call(start_boom)
    deadline = time.monotonic() + 2
    while not runtime.tasks[-1].done() and time.monotonic() < deadline:
        time.sleep(0.02)

    body = client.get("/health").json()

    assert body["status"] == "degraded"
    assert body["dead_tasks"] == ["boom"]


def test_health_is_degraded_when_no_state_was_sent_for_too_long(client):
    from suits.app import HEARTBEAT_LATE_S

    runtime = client.app.state.runtime
    publisher_task = next(t for t in runtime.tasks if t.get_name() == "publisher")
    client.portal.call(publisher_task.cancel)  # cancelled: stuck, but not "dead"
    deadline = time.monotonic() + 2
    while not publisher_task.done() and time.monotonic() < deadline:
        time.sleep(0.02)
    runtime.publisher._latest_at -= HEARTBEAT_LATE_S + 1  # as if the last send was long ago

    body = client.get("/health").json()

    assert body["status"] == "degraded"
    assert body["dead_tasks"] == []


def test_health_names_a_dead_link_task(client):
    from suits.tasks import spawn

    runtime = client.app.state.runtime

    async def boom():
        raise RuntimeError("boom")

    def kill_link():
        runtime.client._tasks.append(spawn(boom(), "tss-broken"))

    client.portal.call(kill_link)
    deadline = time.monotonic() + 2
    while not runtime.client._tasks[-1].done() and time.monotonic() < deadline:
        time.sleep(0.02)

    body = client.get("/health").json()

    assert body["status"] == "degraded"
    assert body["dead_tasks"] == ["tss-broken"]


def test_health_is_degraded_before_the_first_state():
    import asyncio

    from suits.core.publisher import Publisher
    from suits.core.store import Store
    from suits.runtime import Runtime
    from suits.tss.source import TssSource

    source = TssSource()
    store = Store(Mode.SIM)
    app = create_app(Settings(mode=Mode.SIM))
    app.state.runtime = Runtime(Settings(mode=Mode.SIM), source, store,
                                Publisher(source.snapshot, store))
    route = next(r for r in app.routes if getattr(r, "path", "") == "/health")

    body = asyncio.run(route.endpoint())

    assert body["status"] == "degraded"
    assert body["seq"] is None


def test_a_failing_cleanup_does_not_hide_why_startup_failed(monkeypatch):
    import suits.runtime as runtime_module

    def broken_client(*args, **kwargs):
        raise OSError("the real reason")

    async def stop_also_fails(self):
        raise RuntimeError("cleanup failed too")

    monkeypatch.setattr(runtime_module, "TssClient", broken_client)
    monkeypatch.setattr(runtime_module.Runtime, "stop", stop_also_fails)

    with pytest.raises(OSError, match="the real reason"), TestClient(
        create_app(Settings(mode=Mode.SIM))
    ):
        pass


# ---- M2: Origin check and commands over /ws ----


@pytest.mark.parametrize("origin", [
    "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5183",
    "https://localhost:5173", "http://localhost:5173/",
])
def test_the_huds_own_origins_may_connect(client, origin):
    with client.websocket_connect("/ws", headers={"origin": origin}) as ws:
        assert ws.receive_json()["type"] == "state"


def test_a_client_without_an_origin_header_may_connect(client):
    # scripts and tests are not a browser being misused
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "state"


@pytest.mark.parametrize("origin", [
    "http://evil.example", "http://localhost:8080", "http://localhost.evil.example:5173",
    "null", "file://",
])
def test_any_other_origin_is_refused_before_the_socket_opens(client, origin, caplog):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as refused:
        with client.websocket_connect("/ws", headers={"origin": origin}):
            pass

    assert refused.value.code == 1008
    assert "refused a /ws connection" in caplog.text
    assert client.app.state.runtime.publisher.subscriber_count == 0


def test_an_origin_listed_in_settings_may_connect():
    settings = Settings(mode=Mode.SIM, extra_origins=("https://192.168.1.20:5173",))
    with TestClient(create_app(settings)) as c:
        with c.websocket_connect("/ws", headers={"origin": "https://192.168.1.20:5173"}) as ws:
            assert ws.receive_json()["type"] == "state"


def test_settings_read_ports_and_extra_origins_from_the_environment():
    settings = Settings.from_env({"SUITS_CLIENT_PORT": "6000",
                                  "SUITS_ALLOWED_ORIGINS": "https://10.0.0.5:6000/, http://a:1"})

    assert "http://localhost:6000" in settings.allowed_origins()
    assert "http://localhost:5173" not in settings.allowed_origins()
    assert {"https://10.0.0.5:6000", "http://a:1"} <= settings.allowed_origins()


@pytest.mark.parametrize("env", [
    {"SUITS_CLIENT_PORT": "abc"}, {"SUITS_CLIENT_PORT": "70000"},
    {"SUITS_ALLOWED_ORIGINS": "192.168.1.20:5173"},
    {"SUITS_MODE": "replay", "SUITS_RECORDING": "backend/tests/fixtures/captured-tss.jsonl",
     "SUITS_SCENARIO": "fan_failure"},
    {"SUITS_SCENARIO_SPEED": "0"},
])
def test_bad_origin_and_scenario_settings_are_refused(env):
    with pytest.raises(SettingsError):
        Settings.from_env(env)


def test_ack_alert_over_the_socket_marks_the_alert_in_the_next_state(client):
    fake = client.app.state.runtime.fake_tss
    sim = client.app.state.runtime.sim
    with client.websocket_connect("/ws") as ws:
        receive_until(ws, lambda m: m["link"]["tss"] == "ok", timeout=5)
        sim.dynamics.set_fault("oxy")
        msg, _ = receive_until(ws, lambda m: any(a["id"] == "oxygen" for a in m["alerts"]),
                               timeout=6)
        assert msg["alerts"][0]["acked"] is False
        assert fake.state["error"]["oxy_error"] is True

        ws.send_json({"type": "command", "name": "ack_alert", "args": {"id": "oxygen"}})
        msg, waited = receive_until(
            ws, lambda m: any(a["id"] == "oxygen" and a["acked"] for a in m["alerts"]), timeout=2)

    assert waited < 1.0  # notify_change: about 100 ms, not the next heartbeat


def test_toggle_details_over_the_socket_and_bad_frames_do_not_close_it(client, caplog):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_text("garbage")
        ws.send_bytes(b"\x00\x01")
        ws.send_json({"type": "command", "name": "toggle_details", "args": {}})
        msg, _ = receive_until(ws, lambda m: m["ui"]["details_open"], timeout=2)

    assert msg["ui"]["details_open"] is True
    assert "dropped an invalid command" in caplog.text
    assert "dropped a binary /ws frame" in caplog.text


def test_the_state_carries_link_level_alerts_and_ui(client):
    with client.websocket_connect("/ws") as ws:
        msg, _ = receive_until(ws, lambda m: m["link"]["tss"] == "ok", timeout=5)

    assert msg["link"]["level"] == "nominal"
    assert msg["alerts"] == []
    assert msg["ui"] == {"details_open": False}
