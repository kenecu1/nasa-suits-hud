"""Message shapes: the single source of truth.

``State`` (and later ``Command``) cross the wire; their TypeScript types are generated into
client/src/contract.gen.ts by ``npm run contract``. ``TssSnapshot`` is internal to the backend:
it is what the TSS adapter hands to core, so nothing outside ``suits/tss`` sees TSS packets.

Rules: later milestones add fields; they do not rename or remove existing ones. Give a new
field a default so existing constructors keep working (the schema still marks it required).
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field, model_validator

CONTRACT_VERSION = 2

# A section of data older than this is stale: about two missed 1 Hz pushes plus margin.
# Used by the adapter (link status) and by core (value levels), so it lives here.
STALE_AFTER_S = 2.5


class _Model(BaseModel):
    # Every field is present in the JSON we send, so the generated TS fields are not optional.
    # extra="forbid" also makes the generated TS interfaces closed (no [k: string]: unknown).
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        allow_inf_nan=False,
        json_schema_serialization_defaults_required=True,
    )


class LinkStatus(StrEnum):
    """One status for the TSS link (decision A in docs/briefs/M1.md).

    Priority when several apply is decided in suits/tss/source.py (``_link``), not by the order
    here: unassigned, then bad_data, then unreachable, then stale, then ok.
    """

    UNASSIGNED = "unassigned"  # the TSS answered Ack 1: assign our IP to a team in its web UI
    BAD_DATA = "bad_data"  # the newest datagram on some path could not be decoded
    UNREACHABLE = "unreachable"  # nothing valid from any path within STALE_AFTER_S
    STALE = "stale"  # some paths are fresh, at least one has gone quiet
    OK = "ok"


class Level(StrEnum):
    NOMINAL = "nominal"
    CAUTION = "caution"
    WARNING = "warning"
    UNKNOWN = "unknown"  # no value, or not a number
    STALE = "stale"  # last value is older than STALE_AFTER_S


class Mode(StrEnum):
    SIM = "sim"
    REPLAY = "replay"
    LIVE = "live"


# ---- named switch positions (raw flags are turned into these in suits/tss/mapping.py) ----


class DcuPositions(_Model):
    batt: Literal["UMB", "LOCAL"]
    oxy: Literal["PRI", "SEC"]
    comm: Literal["A", "B"]
    fan: Literal["PRI", "SEC"]
    pump: Literal["OPEN", "CLOSED"]
    co2: Literal["A", "B"]


class UiaPositions(_Model):
    eva_power: Literal["ON", "OFF"]
    o2_supply: Literal["OPEN", "CLOSED"]
    water_supply: Literal["OPEN", "CLOSED"]
    water_waste: Literal["OPEN", "CLOSED"]
    o2_vent: Literal["OPEN", "CLOSED"]
    depress: Literal["OPEN", "CLOSED"]


class SuitFaults(_Model):
    fan: bool
    oxy: bool
    power: bool
    scrubber: bool


# ---- internal: adapter -> core ----

Section = Literal["telemetry", "status", "faults", "dcu", "uia"]
SECTIONS: tuple[Section, ...] = ("telemetry", "status", "faults", "dcu", "uia")


class TssSnapshot(_Model):
    """Everything the TSS told us, in our own words. Not sent to the client.

    Sections hold the last value received, however old; None means never received.
    ``ages`` says how old each one is. Core decides what is stale (``STALE_AFTER_S``).
    """

    t: float  # wall-clock time the snapshot was taken (recording time in replay)
    link: LinkStatus
    ages: dict[Section, float]  # seconds since each section last arrived; absent = never
    telemetry: dict[str, float | None]  # TSS names; None = present but not a finite number
    started: bool | None
    faults: SuitFaults | None
    dcu: DcuPositions | None
    uia: UiaPositions | None

    @computed_field
    @property
    def age_s(self) -> float | None:
        """Seconds since the newest valid data from any path; None = never."""
        return min(self.ages.values()) if self.ages else None


# ---- wire: backend -> client ----


class Link(_Model):
    tss: LinkStatus
    age_s: float | None
    mode: Mode


class Eva(_Model):
    started: bool | None
    elapsed_s: float | None
    phase: str | None  # set by procedures (M3)


class SuitValue(_Model):
    """``value`` is None exactly when ``level`` is unknown. A stale value keeps its last number."""

    value: float | None
    unit: str
    level: Level

    @model_validator(mode="after")
    def _value_matches_level(self) -> SuitValue:
        if (self.value is None) != (self.level == Level.UNKNOWN):
            raise ValueError(f"value {self.value!r} does not fit level {self.level}")
        return self


class Suit(_Model):
    values: dict[str, SuitValue]  # all TSS telemetry values, under the TSS's names
    faults: SuitFaults | None  # None = unknown or stale


class State(_Model):
    """Full state, sent once a second and soon after anything changes."""

    type: Literal["state"] = "state"
    v: Literal[2] = 2
    seq: int
    t: float
    link: Link
    eva: Eva
    suit: Suit
    dcu: DcuPositions | None  # None = unknown or stale
    uia: UiaPositions | None


WIRE_MODELS: tuple[type[BaseModel], ...] = (State,)


def json_schema() -> dict:
    """JSON schema of everything that crosses the wire, for TypeScript generation."""
    defs: dict = {}
    for model in WIRE_MODELS:
        schema = model.model_json_schema(mode="serialization", ref_template="#/$defs/{model}")
        defs.update(schema.pop("$defs", {}))
        defs[model.__name__] = schema
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "SuitsContract",
        "description": f"Contract v{CONTRACT_VERSION}. Generated from backend/suits/contract.py.",
        "type": "object",
        "properties": {m.__name__: {"$ref": f"#/$defs/{m.__name__}"} for m in WIRE_MODELS},
        "required": [m.__name__ for m in WIRE_MODELS],
        "additionalProperties": False,
        "$defs": dict(sorted(defs.items())),
    }


if __name__ == "__main__":
    print(json.dumps(json_schema(), indent=2, sort_keys=True))
