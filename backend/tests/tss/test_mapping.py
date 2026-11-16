"""Every raw flag -> named position, one switch at a time (a swapped byte must fail here)."""

import pytest

from suits.tss import codec
from suits.tss.mapping import BadField, dcu_positions, telemetry_values, uia_positions
from suits.tss.source import TssSource

DCU_ORDER = ["batt", "oxy", "comm", "fan", "pump", "co2"]  # byte order in the packet
DCU_ONE = {"batt": "UMB", "oxy": "PRI", "comm": "A", "fan": "PRI", "pump": "OPEN", "co2": "A"}
DCU_ZERO = {"batt": "LOCAL", "oxy": "SEC", "comm": "B", "fan": "SEC", "pump": "CLOSED", "co2": "B"}

UIA_ORDER = ["eva_power", "water_supply", "water_waste", "o2_supply", "o2_vent", "depress"]
UIA_ONE = {"eva_power": "ON", **{f: "OPEN" for f in UIA_ORDER[1:]}}
UIA_ZERO = {"eva_power": "OFF", **{f: "CLOSED" for f in UIA_ORDER[1:]}}


@pytest.mark.parametrize("index", range(6), ids=DCU_ORDER)
def test_each_dcu_byte_moves_only_its_own_switch(index):
    payload = bytes(1 if i == index else 0 for i in range(6))

    positions = dcu_positions(codec.decode_dcu(payload)).model_dump()

    expected = {f: (DCU_ONE[f] if i == index else DCU_ZERO[f]) for i, f in enumerate(DCU_ORDER)}
    assert positions == expected


@pytest.mark.parametrize("index", range(6), ids=UIA_ORDER)
def test_each_uia_byte_moves_only_its_own_switch(index):
    payload = bytes(1 if i == index else 0 for i in range(6)) + b"\xa0\x53\x6a\x35\x4c\x99"

    positions = uia_positions(codec.decode_uia(payload)).model_dump()

    expected = {f: (UIA_ONE[f] if i == index else UIA_ZERO[f]) for i, f in enumerate(UIA_ORDER)}
    assert positions == expected


def test_a_flag_other_than_0_or_1_is_bad_data():
    with pytest.raises(BadField):
        dcu_positions(codec.decode_dcu(bytes([0, 2, 0, 0, 0, 0])))


def test_odd_telemetry_numbers_become_none():
    values = telemetry_values({"a": 1, "b": True, "c": "98", "d": 10**400, "e": 2.5})

    assert values == {"a": 1.0, "b": None, "c": None, "d": None, "e": 2.5}


@pytest.mark.parametrize(
    "reply",
    [
        b"[" * 100_000 + b"]" * 100_000,  # nesting deep enough to hit the recursion limit
        b'{"a": ' + b"9" * 5000 + b"}",  # more digits than Python parses into an int
        b"\xff\xfe",
        b"[1, 2]",
    ],
    ids=["deep", "huge-int", "not-utf8", "not-an-object"],
)
def test_absurd_legacy_replies_are_bad_data_not_a_crash(reply):
    source = TssSource()

    assert source.feed("legacy/1", reply) is None
    assert source.decode_errors == 1
    assert source.snapshot().link == "bad_data"


def test_the_snapshot_carries_elapsed_seconds_from_telemetry():
    source = TssSource()
    source.feed("legacy/1", b'{"oxy_pri_storage": 92.0, "eva_elapsed_time": 600}')

    assert source.snapshot().elapsed_s == 600.0


@pytest.mark.parametrize(
    "reply",
    [b'{"oxy_pri_storage": "92", "heart_rate": null}', b'{"oxy_pri_storage": true}'],
    ids=["strings-and-null", "bool"],
)
def test_telemetry_with_no_usable_number_is_bad_data_not_fresh(reply):
    source = TssSource()

    source.feed("legacy/1", reply)

    snap = source.snapshot()
    assert source.decode_errors == 1
    assert snap.link == "bad_data"
    assert "telemetry" not in snap.ages  # not counted as fresh telemetry
    assert snap.telemetry == {}


def test_telemetry_with_some_numbers_is_kept():
    source = TssSource()

    source.feed("legacy/1", b'{"oxy_pri_storage": 92.0, "heart_rate": null}')

    assert source.snapshot().telemetry == {"oxy_pri_storage": 92.0, "heart_rate": None}


def test_dcu_telemetry_proves_assignment_and_clears_unassigned():
    # A stray late Ack 1 must not leave the link stuck on "unassigned": the TSS only pushes
    # DCU/UIA telemetry to an assigned team.
    source = TssSource()
    source.feed("sub", codec.build_ack(0, codec.AckResult.UNASSIGNED))
    assert source.snapshot().link == "unassigned"

    source.feed("sub", bytes.fromhex("6af55d34001100010003000000000000e5"))

    assert source.snapshot().link != "unassigned"


def test_elapsed_s_is_none_when_telemetry_lacks_it():
    source = TssSource()
    source.feed("legacy/1", b'{"oxy_pri_storage": 92.0}')

    assert source.snapshot().elapsed_s is None
