"""core/commands.py: a command is checked, then changes the Store; anything else is logged and dropped."""

import json
import logging

import pytest

from suits.contract import (
    SECTIONS,
    Command,
    DcuPositions,
    LinkStatus,
    Mode,
    SuitFaults,
    TssSnapshot,
)
from suits.core import commands
from suits.core.store import Store
from suits.sim.fake_tss import default_state


def snapshot(arrival: int, **faults: bool) -> TssSnapshot:
    return TssSnapshot(
        t=1000.0 + arrival,
        link=LinkStatus.OK,
        ages={s: 0.1 for s in SECTIONS},
        arrivals={"telemetry": arrival},
        telemetry=dict(default_state()["telemetry"]),
        started=True,
        faults=SuitFaults(**{"fan": False, "oxy": False, "power": False, "scrubber": False,
                             **faults}),
        dcu=DcuPositions(batt="LOCAL", oxy="PRI", comm="A", fan="PRI", pump="CLOSED", co2="A"),
        uia=None,
    )


def store_with(*fault_names: str) -> Store:
    store = Store(Mode.SIM)
    store.observe(snapshot(1, **{name: True for name in fault_names}))
    return store


def alerts_of(store: Store, arrival: int = 1, *fault_names: str):
    snap = snapshot(arrival, **{name: True for name in fault_names})
    return {a.id: a for a in store.preview(snap).alerts}


@pytest.mark.parametrize(
    "text",
    [
        '{"type":"command","name":"ack_alert","args":{"id":"fan"}}',
        '{"type":"command","name":"ack_alert","args":{}}',
        '{"type":"command","name":"ack_alert"}',
        '{"type":"command","name":"toggle_details","args":{}}',
    ],
)
def test_valid_commands_parse(text):
    assert isinstance(commands.parse(text), Command)


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"type":"state","name":"ack_alert"}',
        '{"type":"command","name":"self_destruct"}',
        '{"type":"command","name":"ack_alert","args":{"id":7}}',
        '{"type":"command","name":"ack_alert","args":{"id":"fan","force":true}}',
        '{"type":"command","name":"ack_alert","extra":1}',
        '{"type":"command","name":"toggle_details","args":{"id":"fan"}}',
        '{"type":"command","name":"ack_alert","args":{"id":"' + "x" * 2000 + '"}}',
    ],
    ids=["not-json", "array", "wrong-type", "unknown-name", "id-not-string", "extra-arg",
         "extra-field", "id-on-toggle", "too-long"],
)
def test_invalid_commands_are_dropped_with_a_log_line(text, caplog):
    store = store_with("fan")
    before = alerts_of(store, 1, "fan")
    with caplog.at_level(logging.WARNING, logger="suits.core.commands"):
        changed = commands.handle(text, store)

    assert changed is False
    assert alerts_of(store, 1, "fan") == before
    assert store.ui.details_open is False
    assert any("dropped" in r.getMessage() for r in caplog.records), caplog.text


def test_ack_with_the_shown_id_acknowledges_that_alert():
    store = store_with("fan")

    changed = commands.handle(json.dumps({"type": "command", "name": "ack_alert",
                                          "args": {"id": "fan"}}), store)

    assert changed is True
    assert alerts_of(store, 1, "fan")["fan"].acked is True


def test_ack_with_an_id_that_is_no_longer_listed_changes_nothing(caplog):
    # decision B: the wearer pressed for an alert that cleared in the meantime
    store = store_with("fan")
    with caplog.at_level(logging.INFO, logger="suits.core.commands"):
        changed = commands.handle('{"type":"command","name":"ack_alert","args":{"id":"oxygen"}}',
                                  store)

    assert changed is False
    assert alerts_of(store, 1, "fan")["fan"].acked is False
    assert "nothing to acknowledge" in caplog.text


def test_ack_never_silences_a_warning_that_arrived_after_the_press():
    # decision B: fan was on top when the wearer pressed; oxygen arrived in between
    store = store_with("fan")
    store.observe(snapshot(2, fan=True, oxy=True))

    commands.handle('{"type":"command","name":"ack_alert","args":{"id":"fan"}}', store)
    alerts = alerts_of(store, 2, "fan", "oxy")

    assert alerts["fan"].acked is True
    assert alerts["oxygen"].acked is False


def test_ack_without_an_id_acknowledges_the_top_alert():
    store = store_with("fan")
    store.observe(snapshot(2, fan=True, oxy=True))  # oxygen is newer, so it is on top

    commands.handle('{"type":"command","name":"ack_alert"}', store)
    alerts = alerts_of(store, 2, "fan", "oxy")

    assert alerts["oxygen"].acked is True
    assert alerts["fan"].acked is False


def test_toggle_details_opens_and_closes_the_details_page():
    store = store_with()
    text = '{"type":"command","name":"toggle_details","args":{}}'

    assert commands.handle(text, store) is True
    assert store.preview(snapshot(1)).ui.details_open is True
    assert commands.handle(text, store) is True
    assert store.preview(snapshot(1)).ui.details_open is False
