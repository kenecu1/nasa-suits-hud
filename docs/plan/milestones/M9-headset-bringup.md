# M9 — Headset bring-up

**Needs the Quest 3S.** Nothing else waits for this milestone.

**Goal:** the HUD runs on the real headset in passthrough: it loads, enters AR, stays connected, takes input, hears and speaks. Every unknown in `docs/plan/headset-risks.md` rows 1–8 gets an answer.

**Builder:** Opus 5.5, in a session with the user wearing or holding the headset. **Fable review:** no.

**Read first:** `docs/plan/headset-risks.md`; notes starting with `quest-`.

## Scope

1. Set up: developer mode, `adb`, `adb reverse` for ports 5173 and 8000, remote DevTools through `chrome://inspect`.
2. Work through risk rows 1–8 in order. For each: run the check, write the result into the matching note (or a new one), fix what fails or apply the fallback.
3. Add a `/device` debug page that shows what the headset reports: session mode, enabled features, frame rate, microphone permission, WebSocket state. It helps the user report what they see.
4. Fix emulator-versus-device differences in the client. If a difference can be reproduced in the emulator, add a test for it.

## Acceptance

Automated (must still pass after any fix): `npm run check`.

On the device (the user confirms each; record pass or fail with a sentence in `docs/walkthroughs/M9.md`):
1. The start page loads and Enter AR shows the room with the HUD over it.
2. With `npm run demo` running, the HUD shows the mission for 5 minutes with `link` ok; the performance overlay shows a steady 72 fps.
3. Each intent works from a controller. Pinch is tried and its reliability noted.
4. Holding talk and asking "how much oxygen do I have" shows the heard text and plays a spoken answer in the headset. If the headset microphone fails, the laptop microphone fallback works.
5. Untethered over Wi-Fi with HTTPS: 10 minutes with the reconnect count shown on `/device`.
6. Each of risk rows 1–8 has a note with the result.
