import asyncio
import json

import websockets


async def main():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        while True:
            msg = json.loads(await ws.recv())
            o2 = msg.get("data", {}).get("telemetry", {}).get("oxy_pri_storage")
            print(f"{msg['type']:<10} reason={msg.get('reason')} age={msg.get('age')} o2={o2}")

asyncio.run(main())