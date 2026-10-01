# Decisions

A record of key project decisions: what we chose, why, and what we gave up. Newest decisions go at the bottom.

---

## Decision 1: HUD tech stack
**Ticket:** SUITS-10
**Date:** October 1, 2026
**Status:** Proposed (pending Vlad's review in the PR)

### Context
The HUD must display live telemetry from NASA's TSS2027. The TSS README requires apps to fetch telemetry over **UDP**: an 8 byte big endian request (timestamp + command number), where command `0` returns `EVA.json` as raw bytes. Telemetry updates once per second. HTTP only serves the TSS's own web page, and the TSS does not support WebSocket.

We have no AR headset and are not competing officially, so the HUD will run on a laptop or tablet.

### Options considered

**Option A: Unity**
Most official SUITS teams used Unity, but because the competition requires a pass through AR headset (usually a HoloLens 2), and Unity is the standard way to build headset apps. That reason doesn't apply to us. NASA's Unity plugin (`TSS_Unity_Plugin_2024`) points to the older TSS and uses HTTP, so it likely won't work with TSS2027's UDP protocol, meaning we'd write our own UDP code in C# anyway. Neither of us knows Unity, and our AI/ML work would still need Python.

**Option B: React web app + Python bridge**
Browsers cannot send UDP, so a web HUD needs a small backend in between. Python handles UDP easily with the built in `socket` and `struct` modules, and the same Python service becomes the home for our ML predictions and LLM voice assistant. React runs in any browser, works on a tablet over Wi Fi, has strong map libraries, and looks great in screenshots and demo videos.

### Comparison

| Criteria | Unity | React + Python bridge |
|---|---|---|
| TSS connection | Custom C# UDP code (plugin likely outdated) | Short Python UDP client |
| Learning curve | New engine for both of us | Familiar languages, new framework |
| Demo / showcase value | Strong with a headset, weaker without | Strong: full screen browser, tablet, webcam overlay |
| Fit with AI/ML layer | Needs a separate Python service anyway | Python bridge already hosts it |
| Fit with no headset | Loses its main advantage | Built for laptop and tablet |
| Career fit | Game / XR development | Full stack + ML, closer to our ML/DS goals |

### Decision
**Option B: a React web app with a Python bridge.**

```
TSS (WSL)  ──UDP──▶  Python bridge  ──WebSocket──▶  React HUD (browser)
                     • polls TSS every 1s
                     • decodes EVA.json
                     • later: ML + voice assistant
```

- **Bridge:** Python. Polls the TSS once per second over UDP, decodes the JSON, and pushes updates to the browser over WebSocket (planned framework: FastAPI).
- **HUD:** React, set up with Vite.
- **Config:** the TSS address and port are settings, never hardcoded, since the IP differs between machines.

### Tradeoffs we accept
- **An extra layer to build and run.** Development means three processes: TSS, bridge, and HUD.
- **No headset experience.** We simulate pass through AR with a dark, full screen HUD, optionally over a live webcam feed.
- **Diverging from most SUITS teams.** Our code won't map directly onto Unity based examples.

### If we get a headset later
Moving to a headset would not mean starting over, because the Python bridge does the hard work (TSS connection, decoding, ML, voice) and the HUD only displays what it receives. Three paths, from easiest to hardest:

| Path | What it means | Effort |
|---|---|---|
| **1. Open the HUD in the headset's browser** | Headsets like Meta Quest have a built in browser. Our React HUD shows up as a floating 2D window. | Very low: works as is |
| **2. Add WebXR to the React app** | WebXR is the browser standard for AR/VR. Libraries like three.js (or React Three Fiber) let panels float in space over the passthrough camera view. Browser support varies by headset, so we'd check the specific device first. | Medium: new rendering layer, same bridge and data |
| **3. Rebuild the display in Unity** | A Unity app connects to our bridge over WebSocket instead of to the TSS directly. Everything in Python stays. | High: new frontend, but no backend rewrite |

**What we do now to keep this cheap:**
- Keep all logic (alerts, predictions, procedure state) in the bridge, so the HUD stays a thin display layer that's easy to replace.
- Keep the bridge to HUD messages in a clear, documented JSON format, so any future frontend (WebXR or Unity) can consume them.
- Design the HUD for dark, low light viewing from the start, which carries over to headsets.

### Effect on other tickets
- **SUITS-11** (telemetry client) becomes the first piece of the Python bridge.
- **SUITS-12** (HUD shows O2) receives the value from the bridge over WebSocket.
- New folders when the code arrives: `bridge/` for Python, and `hud/` for React.

---

## Decision 2: Branch naming
**Ticket:** SUITS-10
**Date:** October 1, 2026

**Format:** `SUITS-<ticket number>-short-description`
**Example:** `SUITS-11-telemetry-client`

- Lowercase words joined by dashes after the ticket key
- One branch per Jira story, owned by one person
- Always start from an up to date `main` (`git checkout main` then `git pull`)
- The ticket key lets Jira link branches and PRs to stories automatically
