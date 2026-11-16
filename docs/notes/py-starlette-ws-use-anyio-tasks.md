In a Starlette/FastAPI WebSocket handler, run concurrent work in an anyio task group, not raw asyncio tasks; cancelling hand-made tasks inside Starlette's anyio cancel scopes made a CancelledError escape now and then.

Found in M1 (2026-11-16), Starlette 1.10, anyio 4, Python 3.12 on Windows.

- Symptom: `with client.websocket_connect("/ws")` in a TestClient test failed about 1 run in 4 with `concurrent.futures.CancelledError` when the block exited. It was the handler task ending cancelled instead of returning.
- Cause: the handler created a sender and a receiver with `asyncio.create_task`, waited with `asyncio.wait(FIRST_COMPLETED)`, then cancelled and gathered them in `finally`. The test client closes the socket and cancels its anyio scope right away; that race sometimes let the cancellation escape the scope.
- Fix (`suits/app.py`): `async with anyio.create_task_group() as group`, with `group.start_soon(...)` for both. Whichever ends first calls `group.cancel_scope.cancel()`. 20 runs in a row then passed.
- Check: run `pytest backend/tests/test_app.py` about ten times after changing `/ws`; a single green run proves little.
