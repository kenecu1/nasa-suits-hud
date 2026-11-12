# M2 — Telemetry, caution and warning, low-light design

**Goal:** the HUD shows all suit data and raises clear, prioritised alerts with a recommended action, in a visual style built for a dim room. NASA requirements 1a, 6a, 6b.

**Builder:** Opus 5.5 (use a Sonnet subagent to wire the 22 fields and write table tests). **Fable review:** no.

**Read first:** `docs/walkthroughs/M1.md`; `docs/archive/hud-layout.md`; "HUD layout rules" in `architecture.md`.

## Scope

1. **Alerts** (`core/alerts.py`, `data/alerts.json`): built from levels, fault flags and link state. Each alert has a stable id, severity (warning above caution), start time, a short title and a recommended action. Actions come from NASA's ranges document:
   - heart rate or temperature high → slow down
   - oxygen pressure off → DCU OXY to SEC, return to lander
   - CO2 pressure high or scrubber above 60% → flip DCU CO2
   - fan off range → DCU FAN to SEC, return to lander
   - battery below 20% → switch battery
2. **No flapping:** a level must hold for 2 samples to raise an alert and be nominal for 3 samples to clear it.
3. **Acknowledge:** `ack_alert` marks the top alert as seen; it stays listed until it clears.
4. **Special states:** EVA not started (no suit alerts), link lost (one link alert, all values `stale`, no suit alerts from old data), unknown values.
5. **Theme** (`theme.ts`): text sizes in dmm (1 dmm = 1 mm at 1 m), starting minimum 24 dmm, panel distance 1.2 m; colours; a dark translucent panel backing; a style per level that differs in colour, shape and word.
6. **Panels:** alert banner (top centre, at most 3 alerts plus a count); consumables (primary and secondary oxygen, battery, scrubber CO2, coolant) as bars with threshold marks; vitals (heart rate, temperature) small, growing when off-nominal; DCU and UIA switch panel; a details page with every value in groups, opened by `toggle_details`; an EVA clock.
7. **Sound:** a short tone on a new warning (Web Audio), driven by a flag in the view model.
8. **Input:** `input/intents.ts` with one binding table per device: keyboard (laptop) and XR controller buttons (headset). First intents: `ack_alert` and `toggle_details`. Later milestones add a row to each table for every new intent.
9. **Sim:** scenarios `fan_failure`, `o2_leak`, `link_loss` as timed value changes on the fake TSS (a minimal player; the full driver comes in M3).

## Acceptance

Backend (pytest)
1. For each of the 22 ranged values: nominal, caution and warning at the edges, from one table.
2. An alert appears only after 2 off-nominal samples and clears only after 3 nominal ones.
3. Each fault flag gives a warning with the right action text. Alert ids stay the same across snapshots. An acknowledged alert stays acknowledged until it clears.
4. Link lost: exactly one link alert, every suit value `stale`, no suit alerts. EVA not started: no suit alerts.
5. Scenario `fan_failure` at high speed: a fan warning with "DCU FAN to SEC" appears; after the switch changes and values recover, it clears.

Client (vitest)
6. Theme: every text size is at least the minimum; text against the panel backing has contrast of at least 7:1; every level style has a different shape and word.
7. View models for every panel, including unknown and stale. The banner shows at most 3 alerts and "+N more".
8. No panel's box overlaps the central 30° × 20° of the view (computed from the rig layout).

End to end (Playwright)
9. Desktop screenshots, compared with a tolerance, for: nominal, caution, warning, link lost, EVA not started.
10. `toggle_details` by keyboard opens a page that lists all telemetry names from the contract. `ack_alert` marks the top alert.
11. Emulated headset: the same view-model checks pass inside the session, and `ack_alert` fires from an emulated controller button.
12. At most 100 draw calls with every panel visible.
