"""M2 acceptance 1: every ranged value gives nominal, caution and warning at its edges, from one table."""
import pytest

from suits.contract import SECTIONS, LinkStatus, TssSnapshot
from suits.core.levels import classify, load_ranges
from suits.core.store import suit_values

RANGES = load_ranges()
MARGIN = RANGES["caution_margin"]


def _cases():
    """(id, name, value, expected) for every ranged value and edge, built from ranges.json."""
    cases = []
    for name, spec in RANGES["ranges"].items():
        lo, hi, check = spec["min"], spec["max"], spec["check"]
        span = hi - lo
        eps = span * 0.001
        band = span * MARGIN
        edges = {
            "low": (lo, -1, check in ("low", "both")),
            "high": (hi, +1, check in ("high", "both")),
        }
        for edge, (limit, out, checked) in edges.items():
            if checked:
                # out is -1 below min and +1 above max, so "inside" is the opposite way
                steps = {
                    "warning": limit + out * eps,
                    "edge": limit,
                    "caution": limit - out * (band - eps),
                    "nominal": limit - out * (band + eps),
                }
                expected = {"warning": "warning", "edge": "caution", "caution": "caution", "nominal": "nominal"}
                for step, value in steps.items():
                    cases.append((f"{name}-{edge}-{step}", name, value, expected[step]))
            else:
                far = limit + out * 10 * span
                cases.append((f"{name}-{edge}-unchecked", name, far, "nominal"))
    return cases


CASES = _cases()
PARAMS = [pytest.param(name, value, expected, id=case_id) for case_id, name, value, expected in CASES]


def _snapshot(name, value):
    return TssSnapshot(
        t=0.0,
        link=LinkStatus.OK,
        ages={s: 0.1 for s in SECTIONS},
        telemetry={name: value},
        started=True,
        faults=None,
        dcu=None,
        uia=None,
    )


def test_table_covers_the_22_ranged_values():
    assert len(RANGES["ranges"]) == 22
    assert {name for _, name, _, _ in CASES} == set(RANGES["ranges"])


def test_every_value_has_all_its_cases():
    for name, spec in RANGES["ranges"].items():
        ids = {case_id for case_id, n, _, _ in CASES if n == name}
        expected = set()
        for edge, matters in (("low", ("low", "both")), ("high", ("high", "both"))):
            if spec["check"] in matters:
                expected |= {f"{name}-{edge}-{s}" for s in ("warning", "edge", "caution", "nominal")}
            else:
                expected.add(f"{name}-{edge}-unchecked")
        assert ids == expected


@pytest.mark.parametrize(("name", "value", "expected"), PARAMS)
def test_classify_level(name, value, expected):
    assert classify(value, RANGES["ranges"][name], MARGIN) == expected


@pytest.mark.parametrize(("name", "value", "expected"), PARAMS)
def test_state_level(name, value, expected):
    result = suit_values(_snapshot(name, value), RANGES)
    assert result[name].level.value == expected
