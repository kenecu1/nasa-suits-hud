import json
from pathlib import Path

from levels import classify, classify_all, load_ranges

# Small limits we control, so the tests don't change when ranges.json changes
LOW = {"min": 20, "max": 100, "check": "low"}      # like an O2 tank: only too low is bad
HIGH = {"min": 0, "max": 60, "check": "high"}      # like a scrubber: only too high is bad
BOTH = {"min": 50, "max": 160, "check": "both"}    # like heart rate: both ends are bad
MARGIN = 0.10

SAMPLE = Path(__file__).parent.parent / "data" / "recordings" / "sample.jsonl"


# ---- classify: one value at a time ----

def test_value_in_the_middle_is_nominal():
    assert classify(60, LOW, MARGIN) == "nominal"
    assert classify(30, HIGH, MARGIN) == "nominal"
    assert classify(100, BOTH, MARGIN) == "nominal"


def test_just_inside_the_caution_zone_is_caution():
    # LOW: the caution zone is 20 to 28 (10% of 80 = 8)
    assert classify(27.9, LOW, MARGIN) == "caution"
    assert classify(28.1, LOW, MARGIN) == "nominal"


def test_exactly_on_the_limit_is_caution_not_warning():
    assert classify(20, LOW, MARGIN) == "caution"
    assert classify(60, HIGH, MARGIN) == "caution"


def test_just_over_the_limit_is_warning():
    assert classify(19.9, LOW, MARGIN) == "warning"
    assert classify(60.1, HIGH, MARGIN) == "warning"
    assert classify(49, BOTH, MARGIN) == "warning"
    assert classify(161, BOTH, MARGIN) == "warning"


def test_only_the_checked_edge_matters():
    assert classify(100, LOW, MARGIN) == "nominal"   # a full tank is fine
    assert classify(0, HIGH, MARGIN) == "nominal"    # an empty scrubber is fine


def test_both_edges_have_a_caution_zone():
    assert classify(55, BOTH, MARGIN) == "caution"     # near the low end
    assert classify(155, BOTH, MARGIN) == "caution"    # near the high end


def test_missing_or_bad_value_is_unknown():
    assert classify(None, LOW, MARGIN) == "unknown"
    assert classify("98", LOW, MARGIN) == "unknown"
    assert classify(True, LOW, MARGIN) == "unknown"    # True is not a real reading


# ---- classify_all: every value at once ----

def test_classify_all_labels_every_value_in_the_config():
    config = {"caution_margin": MARGIN, "ranges": {"o2": LOW, "heart_rate": BOTH}}

    levels = classify_all({"o2": 10, "heart_rate": 100}, True, config)

    assert levels == {"o2": "warning", "heart_rate": "nominal"}


def test_nothing_is_flagged_before_the_eva_starts():
    config = {"caution_margin": MARGIN, "ranges": {"o2": LOW, "heart_rate": BOTH}}

    levels = classify_all({"o2": 0, "heart_rate": 0}, False, config)   # zeros, like the TSS

    assert set(levels.values()) == {"nominal"}


def test_a_value_missing_from_telemetry_is_unknown():
    config = {"caution_margin": MARGIN, "ranges": {"o2": LOW, "heart_rate": BOTH}}

    levels = classify_all({"o2": 50}, True, config)

    assert levels == {"o2": "nominal", "heart_rate": "unknown"}


# ---- the real config file ----

def test_ranges_file_is_well_formed():
    config = load_ranges()

    assert 0 < config["caution_margin"] < 0.5
    for name, limits in config["ranges"].items():
        assert limits["min"] < limits["max"], name
        assert limits["check"] in ("low", "high", "both"), name


def test_real_recording_goes_off_nominal():
    # sample.jsonl is a suit that skipped the egress steps: coolant is empty
    first_line = SAMPLE.read_text(encoding="utf-8").splitlines()[0]
    eva = json.loads(first_line)["eva"]

    levels = classify_all(eva["telemetry"], eva["status"]["started"], load_ranges())

    assert levels["coolant_storage"] == "warning"
    assert set(levels.values()) <= {"nominal", "caution", "warning", "unknown"}
