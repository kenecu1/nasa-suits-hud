# Architecture

```
NASA TSS ──UDP──▶ backend (Python, on the laptop) ──WebSocket──▶ client (browser: laptop page, emulated headset, Quest Browser)
                  │  tss/    adapter: the only code that knows the TSS       ◀── commands, head pose, microphone audio
                  │  sim/    fake TSS + scenario driver
                  │  core/   state, levels, alerts, procedures, navigation, science
                  │  ml/     forecast, range
                  │  voice/  speech-to-text, intents, language model + guardrails, text-to-speech
```

## Decisions and reasons

**1. Web app with WebXR, not Unity.**
The Quest Browser supports passthrough (`immersive-ar`). A web app runs on the laptop today with no headset, tests run in a normal browser toolchain, and AI builder sessions work far better on text code than on a Unity project. The AI and speech stack is Python on the laptop either way. NASA's FAQ says the final TSS speaks WebSocket and JSON, which suits this stack. Cost: no camera access and no native speech in the browser; both are handled below.

**2. The HUD is drawn in WebGL everywhere.**
The Quest Browser cannot show HTML inside an immersive session. So the HUD uses three.js objects (`@react-three/fiber`, panels and text with `@react-three/uikit`) on the laptop too. One scene, three places: laptop page (fixed camera, dark backdrop), emulated headset (`iwer`), real headset. Adding the headset is then input bindings and tuning, not a rewrite.

**3. The backend is the only TSS client and owns all logic.**
The TSS identifies a team by IP and expects one device. Browsers cannot send UDP. So the laptop backend talks to the TSS and the headset talks only to the backend. All mission logic is Python and is tested with pytest without a browser. The client only formats and draws.

**4. One TSS adapter with a stable output.**
`backend/suits/tss/` turns whatever the TSS sends into our own `TssSnapshot`. Today it runs two transports side by side: the new subscription protocol (DCU, UIA, and one of SPM/SSU at a time) and the legacy per-team polling (telemetry, status, faults, position, spectrometer). Raw switch flags become named positions (`"PRI"`, `"OPEN"`) inside the adapter. Recordings are taken at the raw datagram level, so a protocol change is tested by adding a new recording.

**5. Full-state messages, not deltas.**
The backend sends the whole `state` (a few kilobytes) once a second and at once when something changes. A client that connects late or reconnects needs no catch-up logic.

**6. View models between state and drawing.**
Each panel has a pure function `state → view model` (strings, levels, visibility). Unit tests cover the view models. Components only draw them. The current view models are exposed on `window.__hud`, so end-to-end tests can assert HUD content that is not in the DOM.

**7. Intents between input and logic.**
Keyboard (laptop), controller or hand pinch (headset) and voice all produce the same intents (`ack_alert`, `next_step`, `drop_pin`, `toggle_map`, `toggle_details`, `talk`), which become `command` messages. A new input device is a new binding table.

**8. Speech runs on the laptop.**
The browser sends microphone audio to the backend. The backend runs speech-to-text (faster-whisper), answers, runs text-to-speech (Piper) and sends audio back. Common questions are answered from fixed intents with no language model. Other questions go to Claude (`claude-haiku-5-5` by default, set in config) with read-only tools over the mission state plus a short list of allowed actions. Before an answer is spoken, every number in it must match a tool result from that turn; otherwise it is replaced.

**9. ML runs in the backend, trained offline.**
Training data comes from our fast simulator (the TSS's telemetry rules ported to Python, with randomised workload, noise and faults). Real TSS recordings are a held-out test set. Models are small scikit-learn models that run on a CPU once a second.

**10. Position has two sources behind one interface.**
`tss`: the TSS's `posx, posy, heading` (fed by NASA's system, or by our scenario driver). `headset`: the client sends its head pose; the backend maps it to map coordinates with a calibration (origin, heading offset, scale). The source is chosen by `SUITS_POSITION_SOURCE` (default `tss`) or a `set_position_source` command. The headset source is built and tested with the emulator in M4 and calibrated on the device in M10. Heading is degrees, 0 = map north, clockwise.

## Folder layout

```
backend/
  suits/
    contract.py        Pydantic models: TssSnapshot, State, Command (source of truth)
    app.py             FastAPI app: /ws, /health, wiring, modes
    tss/               codec.py, subscription.py, legacy.py, mapping.py, recorder.py, VERSION
    sim/               fake_tss.py, dynamics.py, driver.py
    core/              store.py, levels.py, alerts.py, procedures.py, nav.py, science.py
    ml/                features.py, forecast.py, train.py, evaluate.py
    voice/             stt.py, intents.py, assistant.py, guardrails.py, tts.py
  tests/               mirrors suits/; fixtures/ holds packet hex and golden files
  pyproject.toml
client/
  src/
    contract.gen.ts    generated, do not edit
    net/               WebSocket client, reconnect, audio streaming
    hud/               *.vm.ts view models + tests
    scene/             components, HUD rig (follows the head), XR session setup
    input/             intents.ts, bindings for keyboard / controller / hands
    theme.ts           sizes, colours, level styles
e2e/                   Playwright: desktop/ and xr/
data/
  ranges.json  alerts.json  procedures/  scenarios/  mission/site.json  recordings/  voice/
docs/                  plan/, notes/, walkthroughs/, ml/ (reports), reference/, archive/ (old docs)
vendor/TSS2027/        NASA's TSS at the pinned commit (gitignored, cloned by setup)
models/                speech models (gitignored, downloaded by setup)
```

## Contract (version 2)

Defined in `backend/suits/contract.py`; TypeScript types are generated. Milestones add fields; they do not rename existing ones. Shape:

```
state (backend → client, JSON text)
  type "state", v 2, seq, t
  link      { tss: "ok"|"unreachable"|"unassigned"|"bad_data"|"stale", age_s, mode }
  eva       { started, elapsed_s, phase }
  suit      { values: { <name>: { value, unit, level } }, faults: { fan, oxy, power, scrubber } }
  dcu       { batt, oxy, comm, fan, pump, co2 }   named positions, e.g. oxy "PRI"|"SEC", pump "OPEN"|"CLOSED"
  uia       { eva_power, o2_supply, water_supply, water_waste, o2_vent, depress }   "ON"|"OFF" or "OPEN"|"CLOSED"
  alerts    [ { id, severity, title, action, since, acked } ]                     M2
  procedure { id, title, index, steps: [ { text, actor, status, progress } ] }    M3
  nav       { pos: { x, y, heading, source }, breadcrumbs, pins, pois, keep_out,
              target, route: { points, distance_m, eta_s }, assets }              M4
  forecast  { consumables: { <name>: { time_left_s, low_s, high_s } },
              max_range_m, return_margin_s, turn_back }                           M5
  assistant { status: "idle"|"listening"|"thinking"|"speaking", heard, reply }    M6
  science   { xrf, payload, log }                                                 M7

command (client → backend, JSON text)   { type "command", name, args }
pose    (client → backend, JSON text)   { type "pose", x, y, z, yaw }   about 5 Hz, headset position source
audio   (both ways, binary frames)      16 kHz mono PCM up; speech audio down     M6
```

`level` is `nominal | caution | warning | unknown | stale`. Positions are metres in the TSS map frame. `suit.values` has the 22 ranged values plus `eva_elapsed_time`, under the TSS's names.

## Modes

`SUITS_MODE=sim` (default) starts the fake TSS inside the backend. `replay` feeds a recording through the real decoder. `live` talks to a real TSS. The client does not know which mode is active except through `link.mode`.

## Tests

| Layer | Tool | What it proves |
|---|---|---|
| Packet codec, adapter | pytest + captured packets + fake TSS | We read the TSS correctly; errors are reported, not swallowed |
| Mission logic | pytest + scenarios at high speed | Alerts, procedures, navigation and forecast behave over a whole mission |
| Contract | generated types + drift check | Backend and client agree |
| View models, theme | vitest | Each panel shows the right thing; text size and contrast rules hold |
| Laptop page | Playwright | The real page against the real backend in sim mode |
| Emulated headset | Playwright + `iwer` | The same in a WebXR session: enter AR, HUD follows the head, input works |
| Real TSS | manual smoke script | The adapter still matches NASA's server |
| Real headset | checklist in [headset-risks.md](headset-risks.md) | What emulation cannot show |

## HUD layout rules

The centre of view stays clear (the wearer must see the ground). Alerts top centre. Consumables bottom right. Map top right. Procedure and navigation cue lower left and lower centre edge. Panels sit about 1.2 m away on a rig that follows the head with a delay and only turns, never tilts. Level is shown by colour, shape and a word together. Text sits on a dark translucent backing so contrast does not depend on what is behind it. Earlier layout ideas are in `docs/archive/hud-layout.md` after M1 moves it.
