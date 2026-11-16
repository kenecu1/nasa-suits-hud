"""FastAPI app: /ws sends State, /health says how the backend is. Wiring only.

Run: uvicorn --factory suits.app:create_app  (npm run dev does this)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from suits.runtime import Runtime, start_runtime
from suits.settings import Settings

log = logging.getLogger(__name__)


def _show_backend_logs() -> None:
    """uvicorn configures only its own loggers; show ours (link events) on the console too."""
    suits_log = logging.getLogger("suits")
    if not suits_log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s: %(message)s"))
        suits_log.addHandler(handler)
        suits_log.setLevel(logging.INFO)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg: Settings = settings or Settings.from_env()
    _show_backend_logs()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = await start_runtime(cfg)
        app.state.runtime = runtime
        try:
            yield
        finally:
            await runtime.stop()

    app = FastAPI(title="SUITS HUD backend", lifespan=lifespan)

    def runtime_of(app: FastAPI) -> Runtime:
        return app.state.runtime

    @app.get("/health")
    async def health() -> dict:
        runtime = runtime_of(app)
        publisher = runtime.publisher
        latest = publisher.latest
        dead = runtime.dead_tasks()
        silent = publisher.seconds_since_publish()
        degraded = bool(dead) or silent is None or silent > HEARTBEAT_LATE_S
        return {
            "status": "degraded" if degraded else "ok",
            "mode": cfg.mode.value,
            "tss": latest.link.tss.value if latest else None,
            "seq": latest.seq if latest else None,
            "clients": publisher.subscriber_count,
            "dead_tasks": dead,
        }

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        publisher = runtime_of(app).publisher
        queue = publisher.subscribe()

        # An anyio task group, not raw asyncio tasks: Starlette runs the socket inside anyio
        # cancel scopes, and cancelling hand-made tasks inside them let a CancelledError escape
        # now and then when the client closed (a flaky test showed it).
        try:
            async with anyio.create_task_group() as group:

                async def send_states() -> None:
                    while True:
                        state = await queue.get()
                        try:
                            await websocket.send_text(state.model_dump_json())
                        except WebSocketDisconnect:
                            group.cancel_scope.cancel()
                            return

                async def until_closed() -> None:
                    # Reading notices a closed socket at once, not at the next send.
                    # M1 clients send nothing; command messages arrive here from M2 on.
                    while (await websocket.receive())["type"] != "websocket.disconnect":
                        pass
                    group.cancel_scope.cancel()

                group.start_soon(send_states)
                group.start_soon(until_closed)
        finally:
            publisher.unsubscribe(queue)

    return app


# /health says "degraded" if no State was sent for this long (the heartbeat is 1 s).
HEARTBEAT_LATE_S = 3.0
