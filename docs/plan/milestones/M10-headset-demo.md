# M10 — Passthrough tuning and walk-through demo

**Needs the Quest 3S.** Nothing else waits for this milestone.

**Goal:** the HUD is readable and comfortable in a dim room, real walking moves the astronaut on the map, and a first-person video of a walked mission is recorded.

**Builder:** Opus 5.5 with the user in the headset. **Fable:** only if position mapping cannot be made to work after one session.

**Read first:** `docs/walkthroughs/M9.md`; `docs/plan/headset-risks.md` rows 9–14.

## Scope

1. **Legibility and comfort** (rows 9, 10): in the demo lighting, tune text size, weight, backing opacity, colours, panel distance, follow delay and panel positions with the `/tune` page. Save the result as the default theme. Keep the minimums in the theme tests true; if a minimum must rise, raise it in the test.
2. **Tracking in low light** (row 11): find the lowest light level at which tracking holds on the route. Note it.
3. **Position mapping** (row 12): mark a lander spot and a north direction on the floor. Choose the scale so the demo route fits the room (set in `site.json` calibration). `calibrate` at the lander mark. Walk a measured square and compare the breadcrumbs. Add a `recalibrate` step to the demo script if drift needs it.
4. **Demo route:** a version of `full_mission` for a wearer who really walks: the operator (or the scenario driver in "switches only" mode) does the UIA and DCU switches, faults and rock scan; position comes from the headset.
5. **Recording** (rows 13, 14): record the walk-through in the headset or by casting. Edit a 2–3 minute video. Link it in the README.

## Acceptance

Automated: `npm run check` still green, including theme tests with the tuned values.

On the device (the user confirms each; record in `docs/walkthroughs/M10.md`):
1. In the demo lighting the wearer reads every value on every panel aloud correctly, and can see the floor 2 m ahead with the HUD on.
2. A 5-minute walk with the HUD on is rated comfortable by both Kenny and Vlad, or the remaining issue is written down.
3. Walking a measured 3 m × 3 m square ends within 0.5 m (real) of the start on the map trail after scaling.
4. The full walked mission completes once without restarting anything: egress, walk, sample, fault, turn-back, return, ingress.
5. The video exists and is linked. Risk rows 9–14 each have a note with the result.

## If the headset never arrives or position mapping fails

The laptop video from M8 is the result. For a headset video without walking, use `position_source=tss` with the scenario driver feeding position, standing still.
