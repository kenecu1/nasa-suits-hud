"""FastAPI app: /ws sends State, /health says how the backend is. Wiring only.

Run: uvicorn --factory suits.app:create_app  (npm run dev does this)
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

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

        async def send_states() -> None:
            while True:
                state = await queue.get()
                await websocket.send_text(state.model_dump_json())

        async def until_closed() -> None:
            # Reading notices a closed socket at once, not at the next send.
            # M1 clients send nothing; command messages arrive here from M2 on.
            while (await websocket.receive())["type"] != "websocket.disconnect":
                pass

        sender = asyncio.create_task(send_states())
        receiver = asyncio.create_task(until_closed())
        try:
            await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            publisher.unsubscribe(queue)
            for task in (sender, receiver):
                task.cancel()
            results = await asyncio.gather(sender, receiver, return_exceptions=True)
        for result in results:
            if isinstance(result, (asyncio.CancelledError, WebSocketDisconnect)):
                continue
            if isinstance(result, RuntimeError) and receiver.done():
                continue  # a send raced with the client closing
            if isinstance(result, BaseException):
                log.error("websocket ended with an error", exc_info=result)

    return app


# /health says "degraded" if no State was sent for this long (the heartbeat is 1 s).
HEARTBEAT_LATE_S = 3.0
