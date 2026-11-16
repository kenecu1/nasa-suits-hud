"""The adapter's entry point for live TSS links (real or fake): both dialects side by side.

Code outside ``suits/tss`` starts the link through ``TssClient`` and reads ``TssSource``; it
never imports codec, subscription or legacy (enforced by tests/test_import_boundary.py).
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass

from suits.tss.legacy import LegacyPoller
from suits.tss.source import TssSource
from suits.tss.subscription import Subscription
from suits.tss.transport import Tap

SUBSCRIPTION_PORT = 14141
LEGACY_BASE_PORT = 14142


@dataclass(frozen=True)
class TssAddress:
    host: str
    subscription_port: int = SUBSCRIPTION_PORT
    legacy_port: int = LEGACY_BASE_PORT  # 14142 + team

    @classmethod
    def for_team(cls, host: str, team: int) -> TssAddress:
        if not 0 <= team <= 9:
            raise ValueError(f"TSS team must be 0-9, got {team}")
        return cls(host, SUBSCRIPTION_PORT, LEGACY_BASE_PORT + team)


class TssClient:
    def __init__(self, source: TssSource, address: TssAddress, tap: Tap | None = None) -> None:
        self.source = source
        self.address = address
        self.subscription = Subscription(source, address.host, address.subscription_port, tap)
        self.legacy = LegacyPoller(source, address.host, address.legacy_port, tap)
        self._tasks: list[asyncio.Task] = []

    def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self.subscription.run(), name="tss-subscription"),
            asyncio.create_task(self.legacy.run(), name="tss-legacy"),
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks = []
