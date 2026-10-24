# Bridge

Python code that talks to NASA's TSS. For now it's one script.

## tss_client.py

Asks the TSS for telemetry once per second over UDP, keeps track of whether the connection is alive, and logs the primary O2 level.

### Setup (once)

1. Copy `bridge/config.example.json` to `bridge/config.json`.
2. Open `config.json` and fill in your values:

   | Setting | Meaning |
   |---|---|
   | `tss_ip` | The IP the TSS printed when you started it, **without** `http://` or a port. Example: `172.22.251.151` |
   | `tss_team` | Team number from the TSS web page dropdown (we use `0`) |
   | `timeout_seconds` | How long to wait for a reply before calling it lost (default `2`) |

`config.json` is ignored by git, so your IP stays on your computer. The TSS IP can change after a restart, so update it when that happens.

### Run it

1. Start the TSS (see [docs/setup.md](../docs/setup.md)).
2. On the TSS web page, pick your team and start the EVA.
3. In a second terminal, from the repo root:
   ```
   python bridge/tss_client.py
   ```

### What you should see

A line per second while the TSS is reachable:
```
02:31:07 INFO connected=True age=0s O2=98.97%
```
If the TSS stops answering:
```
02:31:12 WARNING Connection lost: timed out
```
`age` is how many seconds old the last good data is. It grows while the connection is down, and goes back to 0 when the TSS returns. The script recovers by itself.

### Good to know

- A reply that can't be read (bad JSON, missing field) also counts as `connected=False`.
- No installs needed, only Python's built-in libraries.

## server.py

Runs the bridge. It polls the TSS once per second and pushes each reading to the HUD over a WebSocket. The message format is in [docs/contracts/telemetry.md](../docs/contracts/telemetry.md).

**Run it:**
1. One-time install: `python -m pip install -r bridge/requirements.txt`
2. Start the TSS and set up `bridge/config.json` (see above).
3. From the repo root:
```
   cd bridge
   python -m uvicorn server:app --reload --port 8000
```

The HUD connects to `ws://localhost:8000/ws`. Several pages can connect at once. If the TSS is off, the bridge keeps sending messages with `tss_connected: false`.