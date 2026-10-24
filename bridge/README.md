# Bridge

Python code that talks to NASA's TSS and passes its data to the HUD.

- **`server.py`** is the bridge itself: it polls the TSS and pushes messages to the HUD over a WebSocket. It can also record and replay data.
- **`tss_client.py`** is the small console client it is built on. It is also handy for a quick check that the TSS answers.

## Setup (once)

1. Install the packages: `python -m pip install -r bridge/requirements.txt`
2. Copy `bridge/config.example.json` to `bridge/config.json`.
3. Open `config.json` and fill in your values:

   | Setting | Meaning |
   |---|---|
   | `tss_ip` | The IP the TSS printed when you started it, **without** `http://` or a port. Example: `172.22.251.151` |
   | `tss_team` | Team number from the TSS web page dropdown (we use `0`) |
   | `timeout_seconds` | How long to wait for a reply before calling it lost (default `0.5`; keep it under 1 second) |
   | `mode` | `"live"` (default), `"record"` or `"replay"` (see below) |
   | `recording_file` | Only for `"replay"`: the recording to play, as a path from the repo root |

`config.json` is ignored by git, so your IP stays on your computer. The TSS IP can change after a restart, so update it when that happens.

## server.py (the bridge)

Polls the TSS once per second and pushes each result to the HUD over a WebSocket. The message format is in [docs/contracts/telemetry.md](../docs/contracts/telemetry.md).

**Run it:**
1. Start the TSS (see [docs/setup.md](../docs/setup.md)) and start the EVA on its web page.
2. From the repo root:
   ```
   cd bridge
   python -m uvicorn server:app --reload --port 8000
   ```
   It has to be run from inside `bridge/`.

The HUD connects to `ws://localhost:8000/ws`. Several pages can connect at once. If the TSS is off, the bridge keeps sending `tss_error` messages.

## Record and replay

The bridge can save TSS data to a file and play it back later, so you can work on the HUD without WSL or the TSS running. Choose with `mode` in `bridge/config.json`:

| `mode` | What it does |
|---|---|
| `"live"` (default) | Polls the TSS. Nothing is saved. |
| `"record"` | Same as live, and saves every good reply to a new file in `data/recordings/`. |
| `"replay"` | Doesn't touch the TSS. Sends the replies from a recording, one per second, in the same message format as live. At the end of the file it starts over. |

**Record:**
1. Set `"mode": "record"`, start the TSS, and start the EVA.
2. Start the bridge and let it run. Stop it with Ctrl + C.
3. The recording is `data/recordings/run-<date>-<time>.jsonl`, one JSON object per line: `{"t": <time>, "eva": <full TSS reply>}`.

**Replay:**
1. Set `"mode": "replay"` and `"recording_file": "data/recordings/sample.jsonl"`.
2. Start the bridge as above. The TSS does not need to be running. The log says `Replaying sample.jsonl`.

`data/recordings/sample.jsonl` is a committed recording of about 6 minutes with the EVA running. Your own `run-*.jsonl` files are ignored by git.

## tss_client.py (quick console check)

Asks the TSS for telemetry once per second over UDP, keeps track of whether the connection is alive, and logs the primary O2 level.

**Run it:** start the TSS and the EVA, then from the repo root:
```
python bridge/tss_client.py
```

**What you should see:** a line per second while the TSS is reachable:
```
02:31:07 INFO connected=True age=0s O2=98.97%
```
If the TSS stops answering:
```
02:31:12 WARNING Connection lost: timed out
```
`age` is how many seconds old the last good data is. It grows while the connection is down, and goes back to 0 when the TSS returns. The script recovers by itself. Stop it with Ctrl + C.

**Good to know:**
- A reply that can't be read (bad JSON, missing field) also counts as `connected=False`.
- This script uses only Python's built-in libraries. Only `server.py` needs the packages from `requirements.txt`.
