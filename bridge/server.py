import asyncio
import json
import logging
import socket
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from tss_client import load_config, poll_once

RECORDINGS_DIR = Path(__file__).parent.parent / "data" / "recordings"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bridge")

clients = set()

def save_reply(file, data):
    record = {"t": time.time(), "eva": data}
    file.write(json.dumps(record) + "\n")
    file.flush()

async def broadcast(text):
    for ws in list(clients):
        try:
            await ws.send_text(text)
        except Exception:
            clients.discard(ws)

def telemetry_message(payload):
    return {
        "type": "telemetry",
        "version": 1,
        "timestamp": time.time(),
        "data": payload,
    }

def error_message(reason, last_time):
    return {
        "type": "tss_error",
        "version": 1,
        "timestamp": time.time(),
        "reason": reason,
        "age": round(time.time()-last_time, 1) if last_time else None
    }

def replay_replies(path):
    while True:
        with open(path, encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)["eva"]

async def poll_loop(sock, server_address, rec_file, replay):
    last_time = None

    while True:
        try:
            if replay is not None:
                data = next(replay)
            else:
                data = await asyncio.to_thread(poll_once, sock, server_address)
            payload = {"telemetry": data['telemetry'],
                    "status": data['status'],
                    "error": data['error']}
        except OSError as e:
            log.warning("Connection lost: {}".format(e))
            message = error_message("unreachable", last_time)
        except (ValueError, TypeError, KeyError) as e:
            log.warning(f"Bad data format from TSS: {e!r}")
            message = error_message("bad_data", last_time)
        else:
            # only when the poll worked AND data looks correct
            last_time = time.time()
            if rec_file:
                save_reply(rec_file, data)
            message = telemetry_message(payload)

        await broadcast(json.dumps(message))
        await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app):
    config = load_config()
    server_address = (config["tss_ip"], 14142 + config['tss_team'])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 0))
    sock.settimeout(config['timeout_seconds'])   # time out after n secs of not receiving data

    rec_file = None
    if config.get("mode", "live") == "record":
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        name = "run-" + time.strftime("%Y%m%d-%H%M%S") + ".jsonl"
        rec_file = open(RECORDINGS_DIR/name, "a", encoding="utf-8")
        log.info(f"Recording to {name}")

    replay = None
    if config.get("mode", "live") == "replay":
        path = Path(__file__).parent.parent / config["recording_file"]
        replay = replay_replies(path)
        log.info(f"Replaying {path.name}")

    task = asyncio.create_task(poll_loop(sock, server_address, rec_file, replay))   # starts once, when the server starts
    yield
    task.cancel()                    # stops when the server stops
    sock.close()
    if rec_file:
        rec_file.close()

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(websocket)