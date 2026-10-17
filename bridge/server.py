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

async def poll_loop(sock, server_address):
    last_data = None
    last_time = None
    connected = False

    while True:
        try:
            data = await asyncio.to_thread(poll_once, sock, server_address)
            data['telemetry']['oxy_pri_storage']
        except OSError as e:

            connected = False
            log.warning("Connection lost: {}".format(e))
        except (ValueError, TypeError, KeyError) as e:
            connected = False
            log.warning(f"Bad data format from TSS: {e!r}")
        else:
            # only when the poll worked AND data looks correct
            last_data = data
            last_time = time.time()
            connected = True
        
        message = {
            "version": 1,
            "tss_connected": connected,
            "age_seconds": None if last_time is None else int(time.time() - last_time),
            "eva": last_data
        }
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