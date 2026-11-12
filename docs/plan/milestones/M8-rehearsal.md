# M8 — Full mission rehearsal on the laptop

**Goal:** one scripted mission runs from egress to ingress with every feature working together, on the laptop page and in the emulated headset. A laptop demo video is recorded. Everything the headset milestones need that can be built without the headset is built here.

**Builder:** Opus 5.5. **Fable review after:** yes, whole system, before headset time is spent.

**Read first:** all walkthroughs; `docs/plan/headset-risks.md`.

## Scope

1. **Mission script** (`data/scenarios/full_mission.yaml`): egress → walk to point 1 → geology task with a rock scan → a fault (fan) handled with the recommended action → walk on until the turn-back caution → return route → ingress. About 10 minutes at real speed.
2. **Integration fixes:** whatever the full run exposes. Register the remaining voice tools. Range ring uses the planned route.
3. **Live tuning page** (`/tune`, plain HTML on the laptop): change theme tokens (text size, backing opacity, colours, panel distance, follow delay, panel offsets) and see them on every connected client at once; save to `data/theme-overrides.json`.
4. **Headset input bindings** (testable in the emulator): complete the controller table, add a hand-pinch table for every intent, and add a `hide_hud` intent.
5. **Untethered serving:** HTTPS dev server option with the WebSocket proxied through it, so there is one origin (note `quest-loading-dev-page`).
6. **Demo mode:** `npm run demo` (added here) starts everything in sim mode and plays `full_mission`.
7. **README for visitors:** what it is, architecture picture, how to run the demo, links to the two evaluation reports.
8. **Laptop demo video:** the user records the screen while `npm run demo` runs. Add the link to the README.

## Acceptance

1. Backend (pytest): `full_mission` at 20× against the fake TSS. Assert in order: egress complete, arrival at point 1, sample logged, fan warning raised and cleared, turn-back caution raised, arrival at the lander, ingress complete, `eva.phase == done`. No unhandled exception in the log. Every fixed voice intent and every assistant tool is active and answers from the mission state at some checkpoint.
2. Soak (pytest, marked slow): 30 simulated minutes at 20×; resident memory of the backend process (psutil) grows by less than 20% between minute 5 and minute 30; every `state` message validates against the contract; message size stays under 64 kB.
3. Playwright desktop: play `full_mission` at 10×; at five checkpoints `window.__hud` matches expected view models; screenshots saved.
4. Playwright emulated headset: the same five checkpoints inside an `immersive-ar` session; every intent fires from an emulated controller button and from an emulated pinch; `hide_hud` hides all panels except alerts.
5. Tuning: changing the text size on `/tune` changes `window.__hud.theme` on a second connected page within 1 s; saved overrides load on restart; a value below the theme minimum is rejected.
6. HTTPS mode: Playwright loads the page over `https://localhost` (certificate errors ignored) and the WebSocket connects through the proxy.
7. Budget: at most 150 draw calls with everything visible; the client bundle is under 3 MB; reconnect after a backend restart mid-mission restores the full HUD within 3 s.
8. Manual: the full mission against a real TSS in WSL, driven by the scenario driver. Record the result.
9. Manual: the demo video exists and is linked.

## For the review

Ask the reviewer to check: the adapter boundary still holds; nothing in the client computes mission logic; the headset checklist in `headset-risks.md` has no item that could have been tested here; what will most likely break on the device.
