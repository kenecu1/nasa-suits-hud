"""Record raw TSS datagrams and play them back through the real decoder.

One JSON object per line::

    {"t": 1794700000.123, "dir": "in", "ch": "sub", "hex": "6af55d34..."}

``t`` is wall-clock seconds, ``dir`` is "in" (from the TSS) or "out" (sent by us), ``ch`` is the
channel (see source.py). Raw bytes, not decoded values: a decoder change is tested by replaying
old recordings. Replay feeds "in" datagrams to ``TssSource.feed``, the same path live data takes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Literal

from suits.contract import TssSnapshot
from suits.tss.source import TssSource

log = logging.getLogger(__name__)

Direction = Literal["in", "out"]


@dataclass(frozen=True)
class Datagram:
    t: float
    dir: Direction
    ch: str
    data: bytes

    def to_json(self) -> str:
        return json.dumps({"t": round(self.t, 6), "dir": self.dir, "ch": self.ch,
                           "hex": self.data.hex()})


class Recorder:
    """A ``Tap`` that appends every datagram to a JSONL file."""

    def __init__(self, path: Path, wall=time.time) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._wall = wall
        self._file: IO[str] = open(path, "a", encoding="utf-8", newline="\n")
        self.count = 0

    def __call__(self, direction: str, channel: str, data: bytes) -> None:
        if direction not in ("in", "out"):
            raise ValueError(f"direction must be 'in' or 'out', got {direction!r}")
        self._file.write(Datagram(self._wall(), direction, channel, data).to_json() + "\n")
        self._file.flush()
        self.count += 1

    def close(self) -> None:
        self._file.close()


class RecordingError(ValueError):
    pass


def read_recording(path: Path) -> Iterator[Datagram]:
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if row["dir"] not in ("in", "out"):
                    raise ValueError(f"bad dir {row['dir']!r}")
                yield Datagram(float(row["t"]), row["dir"], str(row["ch"]), bytes.fromhex(row["hex"]))
            except (ValueError, KeyError, TypeError) as exc:
                raise RecordingError(f"{path}:{number}: {exc}") from exc


class _Cursor:
    """A clock that reads the recording's time."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def replay_snapshots(path: Path) -> list[TssSnapshot]:
    """Feed every inbound datagram, as fast as possible, and take a snapshot after each.

    Time is the recording's own, so the result is the same on every run (the golden test).
    """
    cursor = _Cursor()
    source = TssSource(clock=cursor, wall=cursor)
    snapshots = []
    for datagram in read_recording(path):
        if datagram.dir != "in":
            continue
        cursor.now = datagram.t
        source.feed(datagram.ch, datagram.data)
        snapshots.append(source.snapshot())
    return snapshots


class Replayer:
    """Plays a recording in real time (times ``speed``) into a ``TssSource``.

    The source's clock must be ``self.clock``: it runs on recording time and keeps running
    after the last datagram, so the link goes unreachable when the recording ends.
    """

    def __init__(self, path: Path, speed: float = 1.0) -> None:
        if speed <= 0:
            raise ValueError("speed must be positive")
        self.path = path
        self.speed = speed
        self.datagrams = [d for d in read_recording(path) if d.dir == "in"]
        if not self.datagrams:
            raise RecordingError(f"{path} has no inbound datagrams")
        self._t0 = self.datagrams[0].t
        self._started_at: float | None = None
        self.finished = asyncio.Event()

    def clock(self) -> float:
        if self._started_at is None:
            return self._t0
        return self._t0 + (time.monotonic() - self._started_at) * self.speed

    async def run(self, source: TssSource) -> None:
        self._started_at = time.monotonic()
        for datagram in self.datagrams:
            delay = (datagram.t - self._t0) / self.speed - (time.monotonic() - self._started_at)
            if delay > 0:
                await asyncio.sleep(delay)
            source.feed(datagram.ch, datagram.data)
        log.info("replay of %s finished (%d datagrams)", self.path.name, len(self.datagrams))
        self.finished.set()
