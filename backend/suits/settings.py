"""Backend settings from environment variables (see CLAUDE.md, Backend modes)."""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from suits.contract import Mode


class SettingsError(ValueError):
    pass


DEFAULT_CLIENT_PORT = 5173
DEFAULT_E2E_CLIENT_PORT = 5183  # e2e/support/ports.ts


def _port(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "")
    if raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise SettingsError(f"{name} must be a port number, got {raw!r}") from None
    if not 1 <= value <= 65535:
        raise SettingsError(f"{name} must be a port number, got {raw!r}")
    return value


def _origins(raw: str) -> tuple[str, ...]:
    """SUITS_ALLOWED_ORIGINS: comma-separated, e.g. "https://192.168.1.20:5173"."""
    # Browsers send scheme://host[:port] in lower case, with no path.
    origins = tuple(o.strip().rstrip("/").lower() for o in raw.split(",") if o.strip())
    bad = [
        o for o in origins
        if not o.startswith(("http://", "https://")) or "/" in o.split("://", 1)[1]
    ]
    if bad:
        raise SettingsError("SUITS_ALLOWED_ORIGINS entries must be http(s)://host[:port] with "
                            f"no path, got {', '.join(bad)}")
    return origins


@dataclass(frozen=True)
class Settings:
    mode: Mode = Mode.SIM
    recording: Path | None = None  # replay: the file to play
    replay_speed: float = 1.0
    tss_host: str | None = None  # live
    tss_team: int = 0
    record: bool = False  # sim/live: save raw datagrams to data/recordings/
    client_port: int = DEFAULT_CLIENT_PORT  # SUITS_CLIENT_PORT: the page's port
    e2e_client_port: int = DEFAULT_E2E_CLIENT_PORT  # SUITS_E2E_CLIENT_PORT: Playwright's page
    extra_origins: tuple[str, ...] = ()  # SUITS_ALLOWED_ORIGINS, e.g. the headset's address
    scenario: str | None = None  # SUITS_SCENARIO: sim only, data/scenarios/<name>.yaml
    scenario_speed: float = 1.0  # SUITS_SCENARIO_SPEED

    def allowed_origins(self) -> frozenset[str]:
        """Browser origins that may open /ws: the HUD's own pages (docs/briefs/M2.md, 8.5).

        Browsers do not apply CORS to WebSockets, so without this any page open on the laptop
        could connect and send commands.
        """
        hosts = ("localhost", "127.0.0.1", "[::1]")
        ports = (self.client_port, self.e2e_client_port)
        own = {f"{scheme}://{host}:{port}" for scheme in ("http", "https") for host in hosts
               for port in ports}
        return frozenset(own | set(self.extra_origins))

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
        if not (math.isfinite(speed) and speed > 0):
            raise SettingsError(f"SUITS_REPLAY_SPEED must be a positive number, got {speed}")
        scenario = env.get("SUITS_SCENARIO") or None
        if scenario is not None and mode != Mode.SIM:
            raise SettingsError("SUITS_SCENARIO plays on the built-in fake TSS: sim mode only")
        if scenario is None and env.get("SUITS_SCENARIO_SPEED"):
            raise SettingsError("SUITS_SCENARIO_SPEED needs SUITS_SCENARIO")
        try:
            scenario_speed = float(env.get("SUITS_SCENARIO_SPEED") or "1")
        except ValueError:
            raise SettingsError("SUITS_SCENARIO_SPEED must be a number") from None
        if not (math.isfinite(scenario_speed) and scenario_speed > 0):
            raise SettingsError(
                f"SUITS_SCENARIO_SPEED must be a positive number, got {scenario_speed}"
            )
        if not 0 <= team <= 9:
            raise SettingsError(f"TSS_TEAM must be 0-9, got {team}")
        return cls(
            mode=mode,
            recording=recording,
            replay_speed=speed,
            tss_host=host,
            tss_team=team,
            record=env.get("SUITS_RECORD", "") in ("1", "true", "yes"),
            client_port=_port(env, "SUITS_CLIENT_PORT", DEFAULT_CLIENT_PORT),
            e2e_client_port=_port(env, "SUITS_E2E_CLIENT_PORT", DEFAULT_E2E_CLIENT_PORT),
            extra_origins=_origins(env.get("SUITS_ALLOWED_ORIGINS", "")),
            scenario=scenario,
            scenario_speed=scenario_speed,
        )
