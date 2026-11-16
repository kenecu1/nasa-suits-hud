"""Value + range -> level. Knows nothing about where a value came from."""

import json
from pathlib import Path

from suits.paths import DATA_DIR

RANGES_FILE = DATA_DIR / "ranges.json"


def load_ranges(path: Path = RANGES_FILE) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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
