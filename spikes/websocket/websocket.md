# Spike: WebSocket and how data reaches the HUD

**Ticket:** SUITS-18
**Date:** October 4, 2026
**Author:** Vlad

## Recommendation

**Use a Python bridge that pushes data to the HUD over WebSocket.** The simpler alternative, the HUD reading the TSS directly over HTTP, does not work: the browser blocks it (tested, see question 2).

This confirms Decision 1 in [decisions.md](../decisions.md).

```
TSS  ──UDP, once per second──▶  Python bridge  ──WebSocket push──▶  HUD page (browser)
       (request / reply)        tss_client.py                        shows the values
```

---

## 1. What is a WebSocket, and how is it different from HTTP?

| | HTTP request | WebSocket |
|---|---|---|
| Who starts | The page asks | The page connects once |
| After the answer | Conversation is over | Connection stays open |
| Who can send | Only the page (server just answers) | Either side, any time |
| Fresh data | The page must ask again (polling) | The server pushes it |

A browser page is not allowed to open raw UDP sockets like our Python client does, so it can only use HTTP or WebSocket.

## 2. Do we need it? Could the HUD just fetch the TSS over HTTP?

**No, the browser blocks it.**

Test: `spikes/websocket/cors-test.html` fetches `http://<IP>:14141/data/instances/0/EVA.json` from a page.

Result, from the browser console:
```
Access to fetch at 'http://172.22.251.151:14141/data/instances/0/EVA.json' from origin 'null'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the
requested resource.
```

- The same URL opens fine in a normal browser tab, so the TSS is working.
- CORS is a browser safety rule: a page may only read data from another address if that server explicitly allows it. The TSS doesn't send that permission.
- Fixing it would mean changing NASA's server code, which we don't do.
- Python is not a browser, so our bridge is not affected.

A bridge also gives us a place for ML predictions, alerts, and the voice assistant.

## 3. Which library, and what does one message look like?

**Library: Python.** The UDP client (SUITS-11) and the future ML code are already Python, so Node would add a second language for no benefit.

- The demo used the `websockets` library (`pip install websockets`). About 15 lines, works.
- `decisions.md` plans **FastAPI**, which does WebSocket plus normal HTTP pages in one server. More to learn, useful if we later need HTTP endpoints too.

**Proposed message (JSON text, sent once per second):**
```json
{
  "tss_connected": true,
  "eva": { "telemetry": { "oxy_pri_storage": 98.97, "...": "..." }, "dcu": {}, "imu": {} }
}
```
- `eva` is the TSS's EVA.json passed through unchanged, so field names match `tss-notes.md`.
- `tss_connected` is `false` (and `eva` is `null`) when the bridge can't reach the TSS. This stops the HUD from showing old values as if they were live (a bug we hit in SUITS-11).

## 4. What happens when the connection drops?

Tested with the counter demo (`counter_server.py` + `counter.html`):

| Test | What happened | What it means for us |
|---|---|---|
| **Server stopped, no reconnect code** | Page showed "Disconnected". Restarting the server did nothing until F5. | Browsers never reconnect a WebSocket by themselves. |
| **Server stopped, page retries every 2 s** | Page reconnected on its own. Counter restarted at 1. | The HUD needs retry code. The restart at 1 is only because the counter lived inside the connection; real telemetry lives in the TSS, so a reconnect gets the current value. |
| **Page closed** | Server printed `ConnectionClosedOK: received 1001 (going away)` and kept running. | Sending to a closed page raises an error. The bridge must catch it and end that connection quietly. |
| **Two pages open** | Each page had its own counter. | The handler runs once per page. The bridge needs ONE loop that polls the TSS and sends the same data to every connected page. |

**Rules for the real bridge and HUD:**
1. HUD: show a clear "disconnected" state and retry every couple of seconds.
2. Bridge: catch `ConnectionClosed` per page; one page leaving must not affect the others.
3. Bridge: poll the TSS in one shared loop and broadcast to all pages.
4. Bridge: tell the HUD when the TSS itself is unreachable (`tss_connected: false`).

---

## Demo files
In `spikes/websocket/`:
- `cors-test.html`: proves the browser blocks direct TSS access
- `counter_server.py`: pushes 1, 2, 3, ... once per second
- `counter.html`: shows the number, with an optional auto-reconnect

Run: `python spikes/websocket/counter_server.py`, then open `counter.html`.
