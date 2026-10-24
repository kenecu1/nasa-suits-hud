import asyncio
from fastapi import WebSocket, FastAPI, WebSocketDisconnect
import json
from contextlib import asynccontextmanager
from tss_client import poll_once, load_config
import logging
import socket
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bridge")

clients = set()

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

async def poll_loop(sock, server_address):
    last_time = None

    while True:
        try:
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

    task = asyncio.create_task(poll_loop(sock, server_address))   # starts once, when the server starts
    yield
    task.cancel()                    # stops when the server stops
    sock.close()

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