The TSS serves about one legacy UDP request per team port every 1.2 s; send one request at a time, or replies queue up and arrive later and later while looking fresh.

Measured live against TSS2027 commit 6293795 in WSL (2026-11-16, M1 builder session 1).

**Why:** `server.c` loops over the HTTP socket, the ten team UDP sockets and the peripheral socket, calling `select` with a 100 ms timeout on each (`wait_on_clients` in `network.c`), and handles at most one datagram per socket per pass. One pass takes about 1.1–1.2 s when the sockets are idle.

**What we saw:** the first M1 poller sent GET 1, 2 and 4 every second (3 requests/s). Over 73 s it sent 74 telemetry GETs and got 22 replies; `eva_elapsed_time` in the replies fell 7 s behind wall time, and `ss -ulnp` showed about 80 KB unread on port 14142 after the backend stopped, draining at about 0.8 datagrams/s. A SET (command 2012) sent meanwhile timed out: it waited behind the queue.

**Rules:**
- One request in flight per team port: send the next when the reply arrives or after a timeout (`suits/tss/legacy.py`). Telemetry gets most turns; status and faults every sixth.
- Expect telemetry about every 1.2–2.4 s and status/faults about every 7 s. Staleness limits per section are in `STALE_AFTER_S` (`suits/contract.py`).
- Anything else that writes to the same port (a scenario driver sending SET 2001–2020) shares this budget. Send SETs one at a time and wait for the 4-byte reply.
- If a previous client flooded the port, its queue is still there: replies stay late until it drains. Restart the TSS if in doubt.
- The fake TSS can emulate this (`FakeTss(legacy_service_s=...)`); `tests/tss/test_link_resilience.py` fails if the poller ever queues requests. Sim mode uses 0.3 s.

**Alternative not used:** `GET /data/instances/<team>/EVA.json` on the HTTP port returns every section in one request (the web UI polls it each second). It is not part of NASA's documented team interface, so the adapter keeps the legacy UDP path.
