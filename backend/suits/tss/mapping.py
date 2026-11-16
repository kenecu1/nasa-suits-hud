"""Raw TSS data -> our own words.

This is the one place where a raw flag becomes a named position (docs/notes/tss-dcu-switch-meaning.md):
flag 1 is the primary side (oxygen PRI, fan PRI, scrubber A, battery UMB, pump OPEN), 0 the
secondary. Nothing after this module sees a raw flag or a TSS JSON section.
"""

from __future__ import annotations

import math
from typing import Any

from suits.contract import DcuPositions, SuitFaults, UiaPositions
from suits.tss.codec import CodecError, DcuFlags, UiaFlags


class BadField(CodecError):
    """A decoded section has a missing or wrongly typed field."""


# field -> (name for flag 0, name for flag 1)
DCU_POSITIONS: dict[str, tuple[str, str]] = {
    "batt": ("LOCAL", "UMB"),
    "oxy": ("SEC", "PRI"),
    "comm": ("B", "A"),
    "fan": ("SEC", "PRI"),
    "pump": ("CLOSED", "OPEN"),
    "co2": ("B", "A"),
}

UIA_POSITIONS: dict[str, tuple[str, str]] = {
    "eva_power": ("OFF", "ON"),
    "o2_supply": ("CLOSED", "OPEN"),
    "water_supply": ("CLOSED", "OPEN"),
    "water_waste": ("CLOSED", "OPEN"),
    "o2_vent": ("CLOSED", "OPEN"),
    "depress": ("CLOSED", "OPEN"),
}

# legacy GET 4 field -> SuitFaults field
FAULT_FIELDS: dict[str, str] = {
    "fan_error": "fan",
    "oxy_error": "oxy",
    "power_error": "power",
    "scrubber_error": "scrubber",
}


def _position(table: dict[str, tuple[str, str]], field: str, flag: int) -> str:
    if flag not in (0, 1):
        raise BadField(f"{field} flag is {flag}, expected 0 or 1")
    return table[field][flag]


def dcu_positions(flags: DcuFlags) -> DcuPositions:
    return DcuPositions(
        **{field: _position(DCU_POSITIONS, field, getattr(flags, field)) for field in DCU_POSITIONS}
    )


def uia_positions(flags: UiaFlags) -> UiaPositions:
    return UiaPositions(
        **{field: _position(UIA_POSITIONS, field, getattr(flags, field)) for field in UIA_POSITIONS}
    )


def telemetry_values(section: dict[str, Any]) -> dict[str, float | None]:
    """Legacy GET 1. Every key is kept under the TSS's name; a non-number becomes None."""
    if not section:
        raise BadField("telemetry section is empty")
    values: dict[str, float | None] = {}
    for name, raw in section.items():
        values[name] = _finite(raw)
    return values


def _finite(raw: Any) -> float | None:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    try:
        value = float(raw)
    except OverflowError:  # an int too big for a float
        return None
    return value if math.isfinite(value) else None


ELAPSED_FIELD = "eva_elapsed_time"


def elapsed_seconds(telemetry: dict[str, float | None]) -> float | None:
    """EVA elapsed time from a mapped telemetry section."""
    return telemetry.get(ELAPSED_FIELD)


def eva_started(section: dict[str, Any]) -> bool:
    """Legacy GET 2."""
    started = section.get("started")
    if not isinstance(started, bool):
        raise BadField(f"status.started is {started!r}, expected true or false")
    return started


def suit_faults(section: dict[str, Any]) -> SuitFaults:
    """Legacy GET 4."""
    values = {}
    for tss_name, our_name in FAULT_FIELDS.items():
        raw = section.get(tss_name)
        if not isinstance(raw, bool):
            raise BadField(f"error.{tss_name} is {raw!r}, expected true or false")
        values[our_name] = raw
    return SuitFaults(**values)
