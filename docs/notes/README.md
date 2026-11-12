# Notes

One lesson per file. The first line of each file is a one-line summary. Read this index, open only what you need.

Add a note when you learn something a later session would otherwise have to rediscover (a TSS quirk, a tool trap, a headset finding). Do not add status reports or summaries of finished work. Fix or delete a note when it turns out to be wrong.

File name: `<area>-<short-lesson>.md`. Areas so far: `tss`, `quest`, `xr`.

## Index

TSS (verified against TSS2027 commit 6293795, 2026-11-10, unless stated)
- [tss-suit-telemetry-is-legacy-only](tss-suit-telemetry-is-legacy-only.md) — suit telemetry, position and spectrometer exist only on the old per-team ports; whole-file command 0 is gone.
- [tss-packet-format](tss-packet-format.md) — header layout, checksum, codes, and real captured packets for tests.
- [tss-readme-payload-sizes-wrong](tss-readme-payload-sizes-wrong.md) — README sizes for UIA, SPM, SSU are wrong; real layouts here.
- [tss-team-must-be-assigned](tss-team-must-be-assigned.md) — a client gets Ack 1 and no data until its IP is assigned to a group and team.
- [tss-build-and-run](tss-build-and-run.md) — HEAD does not compile; how to build and run in WSL.
- [tss-driving-the-sim](tss-driving-the-sim.md) — how to start an EVA, flip switches, inject faults and move the astronaut from a script.
- [tss-protocol-will-change](tss-protocol-will-change.md) — NASA says the final TSS will be WebSocket + JSON; keep all wire knowledge in one adapter.
- [tss-map-coordinates](tss-map-coordinates.md) — map frame, image sizes, lander and task coordinates.
- [tss-dcu-switch-meaning](tss-dcu-switch-meaning.md) — DCU flag 1 = primary, everything starts at 0; battery PRI/SEC is not in the packet.

Quest and WebXR (from web research 2026-11-12, not yet checked on a device)
- [quest-no-dom-overlay](quest-no-dom-overlay.md) — HTML cannot be shown inside an immersive session; the HUD must be drawn in WebGL.
- [quest-speech-runs-on-laptop](quest-speech-runs-on-laptop.md) — no browser speech recognition on Quest; do speech-to-text and text-to-speech on the laptop.
- [quest-no-camera-access](quest-no-camera-access.md) — web pages cannot read the passthrough camera; no computer vision in the headset.
- [quest-loading-dev-page](quest-loading-dev-page.md) — use `adb reverse` so the headset opens `http://localhost`.
- [xr-emulation-headless-unverified](xr-emulation-headless-unverified.md) — running the WebXR emulator inside headless Playwright is plausible but unproven.
