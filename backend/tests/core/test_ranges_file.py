"""data/ranges.json is checked when it is loaded: a bad file stops the backend, it never runs
with wrong levels."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from suits.app import create_app
from suits.contract import Mode
from suits.core import levels
from suits.core.levels import RangesError, load_ranges
from suits.settings import Settings


def good() -> dict:
    return {
        "_source": "test",
        "_how_it_works": "test",
        "caution_margin": 0.1,
        "ranges": {"oxy_pri_storage": {"min": 20, "max": 100, "check": "low", "unit": "%"}},
        "unranged": {"eva_elapsed_time": {"unit": "s"}},
    }


def write(tmp_path, data) -> Path:
    path = tmp_path / "ranges.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_a_good_file_loads(tmp_path):
    assert load_ranges(write(tmp_path, good()))["ranges"]["oxy_pri_storage"]["unit"] == "%"


def test_the_real_file_loads():
    load_ranges()


def bad(change):
    data = good()
    change(data)
    return data


O2 = ("ranges", "oxy_pri_storage")


@pytest.mark.parametrize(
    ("data", "key"),
    [
        (bad(lambda d: d["ranges"]["oxy_pri_storage"].update(check="lo")), "check"),
        (bad(lambda d: d["ranges"]["oxy_pri_storage"].update(min=200)), "oxy_pri_storage"),
        (bad(lambda d: d.update(caution_margin=10)), "caution_margin"),
        (bad(lambda d: d["ranges"]["oxy_pri_storage"].pop("unit")), "unit"),
        (bad(lambda d: d["ranges"]["oxy_pri_storage"].pop("check")), "check"),
        (bad(lambda d: d["ranges"]["oxy_pri_storage"].update(min="20")), "min"),
        (bad(lambda d: d["ranges"]["oxy_pri_storage"].update(colour="red")), "colour"),
        (bad(lambda d: d["unranged"]["eva_elapsed_time"].update(max=5)), "max"),
        (bad(lambda d: d["unranged"]["eva_elapsed_time"].update(unit="")), "unit"),
        (bad(lambda d: d.update(rangez={})), "rangez"),
        (bad(lambda d: d["unranged"].update(oxy_pri_storage={"unit": "%"})), "oxy_pri_storage"),
        (bad(lambda d: d["ranges"]["oxy_pri_storage"].update(max=float("inf"))), "max"),
        (bad(lambda d: d["ranges"]["oxy_pri_storage"].update(min=float("nan"))), "min"),
        (bad(lambda d: d["ranges"]["oxy_pri_storage"].update(min=True)), "min"),
        (bad(lambda d: d["ranges"].update({"": {"min": 0, "max": 1, "check": "low",
                                                 "unit": "%"}})), "name"),
        (bad(lambda d: d.update(caution_margin=0)), "caution_margin"),
        (bad(lambda d: d.update(caution_margin=0.5)), "caution_margin"),
    ],
    ids=[
        "check-lo",
        "min-above-max",
        "margin-10",
        "missing-unit",
        "missing-check",
        "min-not-a-number",
        "unknown-key-in-entry",
        "unranged-with-max",
        "empty-unit",
        "unknown-top-level-key",
        "in-both-ranges-and-unranged",
        "max-infinity",
        "min-nan",
        "min-bool",
        "empty-name",
        "margin-0",
        "margin-0.5",
    ],
)
def test_a_bad_file_names_the_file_and_the_key(tmp_path, data, key):
    path = write(tmp_path, data)

    with pytest.raises(RangesError) as err:
        load_ranges(path)

    message = str(err.value)
    assert message.startswith(f"{path}: ")  # names the file...
    assert key in message[len(f"{path}: "):]  # ...and the key, not just via the file path


def test_a_duplicate_key_is_refused(tmp_path):
    # json.load would keep the last one silently
    path = tmp_path / "ranges.json"
    text = json.dumps(good()).replace(
        '"ranges": {', '"ranges": {"oxy_pri_storage": {"min": 1, "max": 2, "check": "low", '
        '"unit": "%"}, ', 1)
    path.write_text(text, encoding="utf-8")

    with pytest.raises(RangesError, match="duplicate key 'oxy_pri_storage'"):
        load_ranges(path)


def test_a_missing_file_names_the_file(tmp_path):
    with pytest.raises(RangesError, match="nothing.json"):
        load_ranges(tmp_path / "nothing.json")


def test_broken_json_names_the_file(tmp_path):
    path = tmp_path / "ranges.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(RangesError, match="ranges.json"):
        load_ranges(path)


def test_the_backend_refuses_to_start_with_a_bad_file(tmp_path, monkeypatch):
    path = write(tmp_path, bad(lambda d: d["ranges"]["oxy_pri_storage"].update(check="lo")))
    monkeypatch.setattr(levels, "RANGES_FILE", path)

    with pytest.raises(RangesError), TestClient(create_app(Settings(mode=Mode.SIM))):
        pass
