import asyncio
from websockets.asyncio.server import serve

async def handler(websocket):
    # Runs once for each page that connects.
    num_sent = 1
    while True:
        await websocket.send(str(num_sent))
        num_sent += 1
        await asyncio.sleep(1)
    

async def main():
    async with serve(handler, "localhost", 8765) as server:
        print("Server running on ws://localhost:8765")
        await server.serve_forever()

asyncio.run(main())