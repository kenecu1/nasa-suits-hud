"""Backend settings from environment variables (see CLAUDE.md, Backend modes)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from suits.contract import Mode


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    mode: Mode = Mode.SIM
    recording: Path | None = None  # replay: the file to play
    replay_speed: float = 1.0
    tss_host: str | None = None  # live
    tss_team: int = 0
    record: bool = False  # sim/live: save raw datagrams to data/recordings/

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> Settings:
        raw_mode = env.get("SUITS_MODE", "sim").strip().lower()
        try:
            mode = Mode(raw_mode)
        except ValueError:
            raise SettingsError(f"SUITS_MODE must be sim, replay or live, got {raw_mode!r}") from None
        recording = Path(env["SUITS_RECORDING"]) if env.get("SUITS_RECORDING") else None
        if mode == Mode.REPLAY and (recording is None or not recording.is_file()):
            raise SettingsError(f"replay mode needs SUITS_RECORDING=<file>; got {recording}")
        host = env.get("TSS_HOST") or None
        if mode == Mode.LIVE and host is None:
            raise SettingsError("live mode needs TSS_HOST (and TSS_TEAM, default 0)")
        try:
            team = int(env.get("TSS_TEAM", "0"))
            speed = float(env.get("SUITS_REPLAY_SPEED", "1"))
        except ValueError as exc:
            raise SettingsError(f"bad number in settings: {exc}") from None
        if not 0 <= team <= 9:
            raise SettingsError(f"TSS_TEAM must be 0-9, got {team}")
        return cls(
            mode=mode,
            recording=recording,
            replay_speed=speed,
            tss_host=host,
            tss_team=team,
            record=env.get("SUITS_RECORD", "") in ("1", "true", "yes"),
        )
