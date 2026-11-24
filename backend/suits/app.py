"""FastAPI app: /ws sends State and takes commands, /health says how the backend is. Wiring only.

/ws refuses a browser page from any origin but the HUD's own (Settings.allowed_origins), before
accepting the socket. A client that sends no Origin (scripts, tests) is not a browser being
misused and is allowed. Text frames are handed to core/commands.py; this file parses nothing.

Run: uvicorn --factory suits.app:create_app  (npm run dev does this)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from suits.core import commands
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

    origins = cfg.allowed_origins()

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        if origin is not None and origin.rstrip("/") not in origins:
            log.warning("refused a /ws connection from origin %.100r (allowed: the HUD's own "
                        "pages; add others with SUITS_ALLOWED_ORIGINS)", origin)
            await websocket.close(code=1008)  # before accept: the browser sees HTTP 403
            return
        await websocket.accept()
        runtime = runtime_of(app)
        publisher = runtime.publisher
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

                async def read_commands() -> None:
                    # Reading also notices a closed socket at once, not at the next send.
                    while True:
                        message = await websocket.receive()
                        if message["type"] == "websocket.disconnect":
                            break
                        text = message.get("text")
                        if text is None:
                            log.warning("dropped a binary /ws frame (%d bytes): no binary "
                                        "messages before M6", len(message.get("bytes") or b""))
                            continue
                        try:
                            changed = commands.handle(text, runtime.store)
                        except Exception:  # a bug in one command must not close the socket
                            log.exception("command failed: %.200r", text)
                            continue
                        if changed:
                            publisher.notify_change()
                    group.cancel_scope.cancel()

                group.start_soon(send_states)
                group.start_soon(read_commands)
        finally:
            publisher.unsubscribe(queue)

    return app


# /health says "degraded" if no State was sent for this long (the heartbeat is 1 s).
HEARTBEAT_LATE_S = 3.0
