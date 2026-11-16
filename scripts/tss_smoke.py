"""Talk to a real TSS for a few seconds and print what the adapter decodes.

    npm run tss:smoke                      5 s against TSS_HOST, team TSS_TEAM (default 0)
    npm run tss:smoke -- --record          also save the raw datagrams to data/recordings/
    npm run tss:smoke -- --seconds 60 --record     the 60 s recording for a replay fixture

It uses the same adapter as the backend (suits.tss), so if this prints sensible values the
backend's live mode will too. Exit code 0 means DCU, UIA and telemetry all arrived and are
still fresh; anything else exits 1 and says what is missing.

The real TSS answers status and faults only about every 7 s
(docs/notes/tss-legacy-port-is-slow.md), so after a 5 s run the link is often still "stale"
because faults have not come yet. That is reported, not counted as a failure.

Before running: build and start the TSS (docs/notes/tss-build-and-run.md) and assign this
laptop's IP to a team in the TSS web UI (docs/notes/tss-team-must-be-assigned.md).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

from pydantic import BaseModel

from suits.contract import STALE_AFTER_S, LinkStatus, TssSnapshot
from suits.paths import RECORDINGS_DIR, REPO_ROOT
from suits.tss.client import TssAddress, TssClient
from suits.tss.recorder import Recorder
from suits.tss.source import TssSource

HINTS = {
    LinkStatus.UNASSIGNED: "The TSS answered but this laptop's IP is not assigned to a team: "
    "assign it in the TSS web UI (docs/notes/tss-team-must-be-assigned.md).",
    LinkStatus.UNREACHABLE: "Nothing came back. Is the TSS running, and are TSS_HOST and "
    "TSS_TEAM right? (docs/notes/tss-build-and-run.md)",
    LinkStatus.BAD_DATA: "The TSS answered with data the adapter cannot read. Has the TSS "
    "changed since the commit in backend/suits/tss/VERSION?",
    LinkStatus.STALE: "Some data arrived but then stopped, or one part never came.",
}


def pinned_commit() -> str:
    version_file = REPO_ROOT / "backend" / "suits" / "tss" / "VERSION"
    return version_file.read_text(encoding="utf-8").split()[0][:7]


def recording_path(directory: Path) -> Path:
    """real-tss-<commit>.jsonl, or with a timestamp if that file exists (never append to it)."""
    path = directory / f"real-tss-{pinned_commit()}.jsonl"
    if path.exists():
        path = directory / f"real-tss-{pinned_commit()}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    return path


def describe(snapshot: TssSnapshot) -> str:
    """One block of text for one snapshot: link, DCU, UIA, faults and every telemetry value."""
    ages = ", ".join(f"{name} {age:.1f}s" for name, age in sorted(snapshot.ages.items()))
    lines = [f"link: {snapshot.link.value}   ages: {ages or 'nothing received yet'}"]

    def positions(label: str, model: BaseModel | None) -> str:
        if model is None:
            return f"{label}: not received"
        return f"{label}: " + "  ".join(f"{k}={v}" for k, v in model.model_dump().items())

    lines.append(positions("DCU", snapshot.dcu))
    lines.append(positions("UIA", snapshot.uia))
    lines.append(positions("faults", snapshot.faults))
    lines.append(f"EVA started: {snapshot.started}   elapsed: {snapshot.elapsed_s}")
    if snapshot.telemetry:
        values = [f"{name}={value}" for name, value in sorted(snapshot.telemetry.items())]
        lines.append(f"telemetry ({len(values)} values):")
        lines.extend("  " + "  ".join(values[i : i + 3]) for i in range(0, len(values), 3))
    else:
        lines.append("telemetry: not received")
    return "\n".join(lines)


# The three things this check is about. Status and faults come too slowly to demand in 5 s.
REQUIRED = {"dcu": "DCU", "uia": "UIA", "telemetry": "telemetry"}
# A link in one of these states is broken, whatever has arrived.
BROKEN = (LinkStatus.UNASSIGNED, LinkStatus.UNREACHABLE, LinkStatus.BAD_DATA)


def missing(snapshot: TssSnapshot) -> list[str]:
    """What a healthy link must have delivered and has not, or has stopped delivering."""
    received = {"dcu": snapshot.dcu is not None, "uia": snapshot.uia is not None,
                "telemetry": bool(snapshot.telemetry)}
    problems = []
    for section, label in REQUIRED.items():
        age = snapshot.ages.get(section)
        if not received[section] or age is None:
            problems.append(label)
        elif age > STALE_AFTER_S[section]:
            problems.append(f"{label} (last seen {age:.1f} s ago)")
    return problems


def still_waiting(snapshot: TssSnapshot) -> list[str]:
    """Slow sections that have not arrived yet. Worth saying, not a failure."""
    return [section for section in ("status", "faults") if section not in snapshot.ages]


async def smoke(address: TssAddress, seconds: float, recorder: Recorder | None = None,
                every_s: float = 1.0) -> int:
    """Run the link for ``seconds``, printing a snapshot every ``every_s``. Returns the exit code."""
    source = TssSource()
    client = TssClient(source, address, tap=recorder)
    print(f"TSS at {address.host}: subscription port {address.subscription_port}, "
          f"legacy port {address.legacy_port}. Listening for {seconds:g} s.")
    client.start()
    try:
        end = time.monotonic() + seconds
        while (left := end - time.monotonic()) > 0:
            await asyncio.sleep(min(every_s, left))
            print(f"\n--- {seconds - max(0.0, end - time.monotonic()):.0f} s ---")
            print(describe(source.snapshot()))
        final = source.snapshot()
        dead = [task.get_name() for task in client.tasks if task.done()]  # a link loop that died
    finally:
        await client.stop()

    problems = missing(final)
    print()
    if final.link not in BROKEN and not problems and not dead:
        print(f"OK: DCU, UIA and telemetry decoded, link {final.link.value}.")
        if waiting := still_waiting(final):
            print(f"Not received yet: {', '.join(waiting)}. The TSS answers these about every "
                  "7 s; run with --seconds 15 to see them.")
        return 0
    print(f"FAILED: link is {final.link.value}"
          + (f"; missing {', '.join(problems)}" if problems else "")
          + (f"; stopped tasks {', '.join(dead)}" if dead else ""))
    if final.link in HINTS:
        print(HINTS[final.link])
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--host", default=os.environ.get("TSS_HOST"), help="default: TSS_HOST")
    parser.add_argument("--team", type=int, default=int(os.environ.get("TSS_TEAM", "0")),
                        help="team number 0-9 (default: TSS_TEAM or 0)")
    parser.add_argument("--seconds", type=float, default=5.0, help="how long to listen (default 5)")
    parser.add_argument("--record", action="store_true",
                        help="save raw datagrams to data/recordings/real-tss-<commit>.jsonl")
    args = parser.parse_args(argv)
    if not args.host:
        parser.error("no TSS address: set TSS_HOST or pass --host")
    if args.seconds <= 0:
        parser.error("--seconds must be more than 0")
    try:
        address = TssAddress.for_team(args.host, args.team)
    except ValueError as exc:
        parser.error(str(exc))

    recorder = Recorder(recording_path(RECORDINGS_DIR)) if args.record else None
    try:
        code = asyncio.run(smoke(address, args.seconds, recorder))
    except KeyboardInterrupt:
        print("\nStopped.")
        code = 1
    finally:
        if recorder is not None:
            recorder.close()
            print(f"Recording: {recorder.path} ({recorder.count} datagrams)")
    return code


if __name__ == "__main__":
    sys.exit(main())
