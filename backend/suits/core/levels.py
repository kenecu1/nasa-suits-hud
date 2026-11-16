"""Value + range -> level. Knows nothing about where a value came from."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from suits.paths import DATA_DIR

RANGES_FILE = DATA_DIR / "ranges.json"


class RangesError(ValueError):
    """data/ranges.json is missing or wrong. The message names the file and the key."""


class _Entry(BaseModel):
    # strict: "20" is not a number; forbid: a typo'd key is an error, not ignored
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class RangedValue(_Entry):
    min: float
    max: float
    check: Literal["low", "high", "both"]
    unit: str = Field(min_length=1)

    @model_validator(mode="after")
    def _min_below_max(self) -> RangedValue:
        if not self.min < self.max:
            raise ValueError(f"min {self.min} must be below max {self.max}")
        return self


class UnrangedValue(_Entry):
    unit: str = Field(min_length=1)


class RangesFile(_Entry):
    source: str | None = Field(default=None, alias="_source")
    how_it_works: str | None = Field(default=None, alias="_how_it_works")
    caution_margin: float = Field(gt=0, lt=0.5)
    ranges: dict[str, RangedValue] = Field(min_length=1)
    unranged: dict[str, UnrangedValue] = Field(default_factory=dict)


def load_ranges(path: Path | None = None) -> dict:
    """Read and check data/ranges.json. Raises RangesError naming the file and the key.

    Returns the file as a dict (the shape levels.classify reads); every key that store.py
    and classify use is guaranteed present and well typed.
    """
    path = path or RANGES_FILE
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        raise RangesError(f"{path}: cannot read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RangesError(f"{path}: not valid JSON: {exc}") from exc
    try:
        RangesFile.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise RangesError(f"{path}: {problems}") from exc
    return data


def classify(value, limits, margin):
    """Return 'nominal', 'caution', 'warning' or 'unknown' for one value."""
    # True and False count as numbers in Python, so rule them out first
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "unknown"

    lo = limits["min"]
    hi = limits["max"]
    check = limits["check"]

    band = (hi - lo) * margin  # how wide the caution zone is
    low_matters = check in ("low", "both")
    high_matters = check in ("high", "both")

    # warning is checked first: a warning value is also inside the caution zone
    if (low_matters and value < lo) or (high_matters and value > hi):
        return "warning"
    if (low_matters and value < lo + band) or (high_matters and value > hi - band):
        return "caution"
    return "nominal"


def classify_all(telemetry, started, config):
    """Return {value_name: label} for every value listed in config['ranges']."""
    margin = config["caution_margin"]
    levels = {}
    for name, limits in config["ranges"].items():
        if not started:
            levels[name] = "nominal"  # before the EVA starts, values read 0: no alarms
        else:
            levels[name] = classify(telemetry.get(name), limits, margin)
    return levels
