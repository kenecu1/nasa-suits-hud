# Notes

One lesson per file. The first line of each file is a one-line summary. Read this index, open only what you need.

Add a note when you learn something a later session would otherwise have to rediscover (a TSS quirk, a tool trap, a headset finding). Do not add status reports or summaries of finished work. Fix or delete a note when it turns out to be wrong.

File name: `<area>-<short-lesson>.md`. Areas so far: `tss`, `py`, `quest`, `xr`, `e2e`.

## Index

TSS (verified against TSS2027 commit 6293795, 2026-11-10, unless stated)
- [tss-suit-telemetry-is-legacy-only](tss-suit-telemetry-is-legacy-only.md) — suit telemetry, position and spectrometer exist only on the old per-team ports; whole-file command 0 is gone.
- [tss-packet-format](tss-packet-format.md) — header layout, checksum, codes, and real captured packets for tests.
- [tss-readme-payload-sizes-wrong](tss-readme-payload-sizes-wrong.md) — README sizes for UIA, SPM, SSU are wrong; real layouts here (sizes as of 7dfc42b).
- [tss-team-must-be-assigned](tss-team-must-be-assigned.md) — a client gets Ack 1 and no data until its IP is assigned to a group and team.
- [tss-build-and-run](tss-build-and-run.md) — rebuild in WSL after every pull (a stale binary ignores Subscribe); build command and how to run.
- [tss-driving-the-sim](tss-driving-the-sim.md) — how to start an EVA, flip switches, inject faults and move the astronaut from a script.
- [tss-protocol-will-change](tss-protocol-will-change.md) — NASA says the final TSS will be WebSocket + JSON; keep all wire knowledge in one adapter.
- [tss-map-coordinates](tss-map-coordinates.md) — map frame, image sizes, lander and task coordinates.
- [tss-dcu-switch-meaning](tss-dcu-switch-meaning.md) — DCU flag 1 = primary, everything starts at 0; battery PRI/SEC is not in the packet.
- [tss-legacy-port-is-slow](tss-legacy-port-is-slow.md) — about one legacy request per team port per 1.2 s; send one at a time or replies queue up and go stale.

Python (verified in M1, 2026-11-16)
- [py-windows-udp-goes-deaf](py-windows-udp-goes-deaf.md) — on Windows' Proactor loop a UDP socket stops receiving after "port unreachable"; close and reopen it.
- [py-starlette-ws-use-anyio-tasks](py-starlette-ws-use-anyio-tasks.md) — in a WebSocket handler use an anyio task group; raw asyncio tasks made a CancelledError escape now and then.

Quest and WebXR (from web research 2026-11-12, not yet checked on a device)
- [quest-no-dom-overlay](quest-no-dom-overlay.md) — HTML cannot be shown inside an immersive session; the HUD must be drawn in WebGL.
- [quest-speech-runs-on-laptop](quest-speech-runs-on-laptop.md) — no browser speech recognition on Quest; do speech-to-text and text-to-speech on the laptop.
- [quest-no-camera-access](quest-no-camera-access.md) — web pages cannot read the passthrough camera; no computer vision in the headset.
- [quest-loading-dev-page](quest-loading-dev-page.md) — use `adb reverse` so the headset opens `http://localhost`.

WebXR emulation and end-to-end tests (verified in M1, 2026-11-16)
- [xr-emulation-headless-works](xr-emulation-headless-works.md) — an `immersive-ar` session runs in headless Chromium with `iwer`, if `installRuntime` is forced. (Was `xr-emulation-headless-unverified`.)
- [xr-dev-emulator-needs-one-three](xr-dev-emulator-needs-one-three.md) — the emulator control panel needs `resolve.dedupe: ["three"]`; the library's built-in emulator does not install in Chromium.
- [e2e-backend-link-settles-after-start](e2e-backend-link-settles-after-start.md) — the sim link takes about 3 s to reach `ok` after a backend start; tests wait for it.
