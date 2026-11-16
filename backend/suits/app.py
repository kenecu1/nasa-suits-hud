"""FastAPI app: /ws sends State, /health says how the backend is. Wiring only.

Run: uvicorn --factory suits.app:create_app  (npm run dev does this)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from suits.runtime import Runtime, start_runtime
from suits.settings import Settings

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = await start_runtime(settings)
        app.state.runtime = runtime
        try:
            yield
        finally:
            await runtime.stop()

    app = FastAPI(title="SUITS HUD backend", lifespan=lifespan)

    def runtime_of(app: FastAPI) -> Runtime:
        return app.state.runtime

    @app.get("/health")
    def health() -> dict:
        runtime = runtime_of(app)
        latest = runtime.publisher.latest
        return {
            "status": "ok",
            "mode": settings.mode.value,
            "tss": latest.link.tss.value if latest else None,
            "seq": latest.seq if latest else None,
            "clients": runtime.publisher.subscriber_count,
        }

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        publisher = runtime_of(app).publisher
        queue = publisher.subscribe()
        try:
            while True:
                state = await queue.get()
                await websocket.send_text(state.model_dump_json())
        except WebSocketDisconnect:
            pass
        except RuntimeError as exc:  # sending on a socket the client already closed
            log.debug("websocket closed while sending: %s", exc)
        finally:
            publisher.unsubscribe(queue)

    return app
