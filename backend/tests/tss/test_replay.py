"""Acceptance 6: replaying a recording gives the same TssSnapshot sequence as its golden file.

Golden files sit next to each recording as <name>.golden.jsonl. To regenerate after a deliberate
decoder change, run with SUITS_UPDATE_GOLDEN=1 and review the diff before committing.
"""

import json
import os
from pathlib import Path

import pytest

from suits.contract import LinkStatus
from suits.paths import RECORDINGS_DIR
from suits.tss.recorder import (
    Recorder,
    RecordingError,
    read_recording,
    replay_snapshots,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
RECORDINGS = sorted([FIXTURES / "captured-tss.jsonl", *RECORDINGS_DIR.glob("real-tss-*.jsonl")])


def golden_path(recording: Path) -> Path:
    return FIXTURES / f"{recording.stem}.golden.jsonl"


def as_lines(recording: Path) -> list[str]:
    return [s.model_dump_json() for s in replay_snapshots(recording)]


@pytest.mark.parametrize("recording", RECORDINGS, ids=lambda p: p.name)
def test_replay_matches_golden(recording):
    lines = as_lines(recording)
    golden = golden_path(recording)
    if os.environ.get("SUITS_UPDATE_GOLDEN") == "1":
        golden.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    assert golden.exists(), f"no golden file; run with SUITS_UPDATE_GOLDEN=1 to create {golden}"
    assert lines == golden.read_text(encoding="utf-8").splitlines()


def test_replay_is_deterministic():
    recording = FIXTURES / "captured-tss.jsonl"

    assert as_lines(recording) == as_lines(recording)


def test_captured_recording_goes_through_the_whole_decoder():
    snapshots = replay_snapshots(FIXTURES / "captured-tss.jsonl")
    links = {s.link for s in snapshots}
    last = snapshots[-1]

    assert LinkStatus.BAD_DATA in links  # the corrupt packet and the truncated JSON
    assert last.link == LinkStatus.OK
    assert last.dcu.oxy == "PRI"  # flipped from SEC to PRI in second 3
    assert snapshots[5].dcu.oxy == "SEC"  # first DCU packet: all flags 0
    assert last.started is True
    assert last.telemetry["coolant_storage"] == 0  # the sample run skipped egress


REAL = RECORDINGS_DIR / "real-tss-6293795.jsonl"  # committed (acceptance 16)


def test_real_recording_shows_what_was_done_to_the_tss():
    # 70 s against TSS2027 6293795 in WSL, 2026-11-16. During it: fan switch to PRI (~25 s),
    # fan fault on (~35 s) and off (~50 s), oxygen switch to SEC (~58 s).
    snapshots = replay_snapshots(REAL)
    t0 = snapshots[0].t
    after_start = [s for s in snapshots if s.t - t0 > 8]

    def seen(predicate):
        return [round(s.t - t0) for s in snapshots if predicate(s)]

    assert all(s.link == LinkStatus.OK for s in after_start)
    assert all(len(s.telemetry) == 23 and s.started for s in after_start)
    assert all(s.ages["telemetry"] < 4.0 for s in after_start)  # the poller kept up
    assert seen(lambda s: s.faults is not None and s.faults.fan)[0] in range(35, 45)
    assert snapshots[-1].faults.fan is False
    assert seen(lambda s: s.dcu is not None and s.dcu.fan == "PRI")[0] in range(25, 30)
    assert seen(lambda s: s.dcu is not None and s.dcu.oxy == "SEC")[0] in range(58, 62)


def test_recorder_writes_what_replay_reads(tmp_path):
    path = tmp_path / "rec.jsonl"
    clock = iter([10.0, 10.5])
    recorder = Recorder(path, wall=lambda: next(clock))
    recorder("out", "sub", b"\x01\x02")
    recorder("in", "legacy/1", b'{"a": 1}')
    recorder.close()

    rows = list(read_recording(path))

    assert [(r.t, r.dir, r.ch, r.data) for r in rows] == [
        (10.0, "out", "sub", b"\x01\x02"),
        (10.5, "in", "legacy/1", b'{"a": 1}'),
    ]
    assert json.loads(path.read_text(encoding="utf-8").splitlines()[0])["hex"] == "0102"


def test_a_broken_recording_line_names_the_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"t": 1, "dir": "in", "ch": "sub", "hex": "00"}\nnot json\n', encoding="utf-8")

    with pytest.raises(RecordingError, match="bad.jsonl:2"):
        list(read_recording(path))
