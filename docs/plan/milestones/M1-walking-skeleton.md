# M1 — Walking skeleton

**Goal:** one suit value and one switch travel from the TSS to a WebGL HUD panel, on the laptop page and inside an emulated headset session, with record/replay and tests at every layer. This milestone sets the patterns the others copy, so do the patterns properly and keep the features minimal.

**Builder:** Opus 5.5. **Fable review after:** yes. Stop when done and tell the user.

**Suggested split:** session 1 does parts 1–6 (backend), session 2 does parts 7–10 (client and end-to-end). End session 1 with `npm run check:fast` green.

**Read first:** `docs/plan/architecture.md`; notes `tss-suit-telemetry-is-legacy-only`, `tss-packet-format`, `tss-readme-payload-sizes-wrong`, `tss-team-must-be-assigned`, `tss-dcu-switch-meaning`, `tss-driving-the-sim`, `tss-build-and-run`, `quest-no-dom-overlay`, `xr-emulation-headless-unverified`.

## Scope

1. **Repo reset.** Create the layout in `architecture.md`. Move `bridge/levels.py` → `backend/suits/core/levels.py`, `bridge/ranges.json` → `data/ranges.json`, `tests/test_levels.py` → `backend/tests/core/`. Change `levels.py` to load ranges from `data/`. Keep `data/recordings/sample.jsonl` as `backend/tests/fixtures/legacy-sample.jsonl` (a real 6-minute TSS run in the old JSON format; one level test reads it and M5 uses it). Delete `bridge/`, `hud/`, `spikes/`, `server/` and the other old tests. Create an empty `client/` package so generated types have a home. `npm run setup` also clones the TSS at the pinned commit into `vendor/TSS2027` (gitignored; see `tss-build-and-run`). Move `docs/decisions.md`, `tss-notes.md`, `setup.md`, `hud-layout.md` and `contracts/` to `docs/archive/`, each with a first line "Superseded by docs/plan". Root `package.json` with the commands in `CLAUDE.md`. Update CI to run `npm run check`.
2. **TSS adapter** (`backend/suits/tss/`), asyncio UDP:
   - `codec.py`: build and parse packets, checksum, typed errors.
   - `subscription.py`: subscribe to DCU and UIA, re-send until Ack, report `unassigned` on Ack 1.
   - `legacy.py`: poll commands 1 (telemetry), 2 (status), 4 (faults) once a second.
   - `mapping.py`: raw data → `TssSnapshot`, switch flags → named positions.
   - `VERSION`: the TSS commit this was verified against.
3. **Fake TSS** (`backend/suits/sim/fake_tss.py`): a localhost UDP server that speaks both paths, answers Ack 0/1/2, accepts the legacy commands in `tss-driving-the-sim` (2001–2004, 2009–2020), and serves values from a dict that tests can change. Static values are enough here.
4. **Recorder and replayer** (`tss/recorder.py`): raw datagrams with direction and time, one JSON object per line, in `data/recordings/`. Replay feeds the same decoder.
5. **Contract v2, first part:** `TssSnapshot`, `State` with `link`, `eva`, `suit` (all telemetry values with unit and level), `dcu`, `uia`. Schema export, TypeScript generation, drift check.
6. **Backend app:** modes `sim | replay | live`; `/ws` sends `state` every second and on change; `/health`.
7. **Client:** Vite, React, `@react-three/fiber`, `@react-three/xr`, `@react-three/uikit`, zustand. WebSocket client with automatic reconnect. A HUD rig that follows the head. One panel: primary oxygen percent with level shown by colour, shape and word; DCU oxygen switch position; link status. Start page with an Enter AR button. Laptop view with a fixed camera and dark backdrop. `window.__hud` test hook. `theme.ts` with the first tokens. Backend URL derived from the page origin.
8. **End-to-end harness:** Playwright projects `desktop` and `xr` (emulated Quest 3 with `iwer`).
9. **`scripts/tss_smoke.py`:** against a real TSS, print decoded DCU, UIA and telemetry for 5 seconds, and optionally save a recording.
10. **Docs:** fill in the real commands in `CLAUDE.md`, write `docs/walkthroughs/M1.md`, update notes.

Out of scope: more than one panel, alerts, any other device, visual polish.

## Acceptance (all run by `npm run check` unless marked)

Backend (pytest)
1. Each captured packet in `tss-packet-format` decodes to the fields stated there. Building a Subscribe-to-DCU packet with timestamp `0x6af55d2c` gives exactly `6af55d2c000d000f00010001ec`.
2. A packet with a wrong checksum, a length field that differs from its size, or fewer than 11 bytes raises a typed error and does not crash the receive loop.
3. The 12-byte UIA payload decodes from its first 6 bytes. A 5-byte payload is rejected.
4. Against the fake TSS: first `TssSnapshot` within 3 s. If the fake drops the first Subscribe, the client retries and succeeds. If the fake answers Ack 1, `link.tss` is `unassigned`.
5. Against the fake TSS: telemetry, status and faults are parsed. If the fake goes silent, `link.tss` becomes `unreachable` within 3 s and `age_s` grows. Bad JSON gives `bad_data`.
6. Replaying the fixture recording produces the same sequence of `TssSnapshot` as the golden file.
7. A test fails if any module outside `suits/tss` and `suits/sim` imports `codec`, `subscription` or `legacy`.
8. The 12 ported level tests pass unchanged in meaning.
9. App in sim mode: a WebSocket client receives `state` with `v == 2`; primary oxygen equals the fake's value with level `nominal`; setting the fake's value to 15 gives level `warning` within 2 s; `dcu.oxy` is a named position, not a boolean.
10. `npm run contract -- --check` fails when `contract.gen.ts` is out of date.

Client (vitest)
11. The oxygen panel view model for nominal, caution, warning, unknown and stale input.
12. The WebSocket client reconnects with backoff after a close, using a fake socket.

End to end (Playwright, backend in sim mode)
13. Desktop: `window.__hud.panels.o2.text` matches the backend value. Stop the backend: the link panel shows offline within 4 s. Start it again: the page recovers without a reload. A screenshot is saved.
14. Emulated headset: after Enter AR an `immersive-ar` session is active. The panel is inside the emulated view. After the emulated head turns 90° and 2 s pass, the panel is inside the view again.
15. The scene uses at most 50 draw calls (`renderer.info`).

If item 14 cannot run headless, follow the fallback in `xr-emulation-headless-unverified`: move the `xr` project to `npm run e2e:xr` (headed, local only), take it out of `npm run check`, update `CLAUDE.md`, record what happened in that note, and tell the user.

Screenshots in this and later milestones follow the policy in `CLAUDE.md` (Testing).

Manual, not in CI
16. With a real TSS in WSL: `npm run tss:smoke` prints live DCU, UIA and telemetry. Save a 60 s recording as `data/recordings/real-tss-<commit>.jsonl` and use it as the fixture for item 6. If the real TSS cannot be run in this session, say so in the walkthrough and leave the fixture built from the captured packets.
