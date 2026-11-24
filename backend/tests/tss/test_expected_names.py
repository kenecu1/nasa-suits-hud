"""Decision A (docs/briefs/M2.md): expected telemetry names that do not arrive are reported.

The values that did arrive are kept; the missing ones are unknown; the link is bad_data while
any are missing; one caution alert names them; tss:smoke exits 1.
"""

import json

from suits.contract import LinkStatus, Mode
from suits.core.levels import load_ranges
from suits.core.store import Store
from suits.sim.fake_tss import default_state
from suits.tss import codec, mapping
from suits.tss.source import TssSource, legacy_channel

TELEMETRY = legacy_channel(codec.LegacyCommand.TELEMETRY)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def full_telemetry() -> dict:
    return dict(default_state()["telemetry"])


def feed_telemetry(source: TssSource, body: dict) -> None:
    source.feed(TELEMETRY, json.dumps(body).encode())


def test_expected_names_are_exactly_the_names_in_ranges_json():
    ranges = load_ranges()

    assert set(mapping.EXPECTED_TELEMETRY) == set(ranges["ranges"]) | set(ranges["unranged"])
    assert len(mapping.EXPECTED_TELEMETRY) == len(set(mapping.EXPECTED_TELEMETRY)) == 23


def test_the_fake_tss_sends_every_expected_name():
    assert mapping.missing_telemetry(mapping.telemetry_values(full_telemetry())) == ()


def test_a_missing_name_is_reported_and_the_rest_is_kept():
    body = full_telemetry()
    del body["oxy_pri_storage"]

    values = mapping.telemetry_values(body)

    assert mapping.missing_telemetry(values) == ("oxy_pri_storage",)
    assert values["heart_rate"] == body["heart_rate"]


def test_a_name_that_is_present_but_not_a_number_is_not_missing():
    body = full_telemetry()
    body["heart_rate"] = "n/a"

    values = mapping.telemetry_values(body)

    assert values["heart_rate"] is None
    assert mapping.missing_telemetry(values) == ()


def test_a_renamed_field_is_translated_to_our_name(monkeypatch):
    body = full_telemetry()
    body["primary_oxygen"] = body.pop("oxy_pri_storage")
    monkeypatch.setitem(mapping.RENAMED, "primary_oxygen", "oxy_pri_storage")

    values = mapping.telemetry_values(body)

    assert values["oxy_pri_storage"] == 92.0
    assert mapping.missing_telemetry(values) == ()


def fresh_source(clock: Clock) -> TssSource:
    """A source that has every section, so the link would be ok without the missing name."""
    source = TssSource(clock=clock, wall=clock)
    state = default_state()
    source.feed(legacy_channel(codec.LegacyCommand.STATUS), json.dumps(state["status"]).encode())
    source.feed(legacy_channel(codec.LegacyCommand.ERROR), json.dumps(state["error"]).encode())
    source.feed("sub", codec.build_telemetry(0, codec.Device.DCU, codec.encode_dcu(
        codec.DcuFlags(batt=0, oxy=1, comm=1, fan=1, pump=0, co2=1))))
    source.feed("sub", codec.build_telemetry(0, codec.Device.UIA, codec.encode_uia(
        codec.UiaFlags(eva_power=0, water_supply=0, water_waste=0, o2_supply=0, o2_vent=0,
                       depress=0))))
    return source


def test_link_is_ok_with_every_name_and_bad_data_while_one_is_missing():
    clock = Clock()
    source = fresh_source(clock)
    feed_telemetry(source, full_telemetry())
    assert source.snapshot().link == LinkStatus.OK

    body = full_telemetry()
    del body["oxy_pri_storage"]
    feed_telemetry(source, body)
    snapshot = source.snapshot()

    assert snapshot.link == LinkStatus.BAD_DATA
    assert snapshot.missing == ("oxy_pri_storage",)

    feed_telemetry(source, full_telemetry())  # NASA puts it back
    assert source.snapshot().link == LinkStatus.OK
    assert source.snapshot().missing == ()


def test_a_silent_tss_is_unreachable_even_with_names_missing():
    clock = Clock()
    source = fresh_source(clock)
    body = full_telemetry()
    del body["oxy_pri_storage"]
    feed_telemetry(source, body)

    clock.now += 3.0  # nothing heard for longer than LINK_SILENT_AFTER_S

    assert source.snapshot().link == LinkStatus.UNREACHABLE


def test_arrivals_count_every_reply_even_an_unchanged_one():
    clock = Clock()
    source = fresh_source(clock)
    feed_telemetry(source, full_telemetry())
    feed_telemetry(source, full_telemetry())

    assert source.snapshot().arrivals["telemetry"] == 2


def test_through_the_store_a_missing_value_is_unknown_and_one_caution_names_it():
    clock = Clock()
    source = fresh_source(clock)
    body = full_telemetry()
    del body["oxy_pri_storage"]
    feed_telemetry(source, body)
    store = Store(Mode.SIM)
    snapshot = source.snapshot()

    store.observe(snapshot)
    state = store.preview(snapshot)

    assert state.suit.values["oxy_pri_storage"].level == "unknown"
    assert state.suit.values["heart_rate"].level == "nominal"
    assert state.link.tss == "bad_data" and state.link.level == "warning"
    assert [(a.id, a.severity) for a in state.alerts] == [("data", "caution")]
    assert "1 FIELD MISSING" in state.alerts[0].title
    assert "oxy_pri_storage" in state.alerts[0].action
