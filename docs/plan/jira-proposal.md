# Jira changes (approved and applied 2026-11-12)

Project SUITS on kenecu12.atlassian.net. Read on 2026-11-12: 5 epics, 46 stories and tasks (SUITS-1 to SUITS-54), 19 done.

**Idea:** Jira becomes a status board with one story per milestone. The milestone file in the repo is the spec; the story links to it. Old stories that the new plan covers are closed with a pointer, so nothing is tracked twice.

## Keep as they are

All 19 issues already Done (SUITS-6 to 12, 15, 17 to 27). They are history.

## Close as Done

| Issue | Why |
|---|---|
| SUITS-31 Bridge: classify every suit value | Finished and tested on its branch (18 tests pass). The code moves into the new backend in M1. |

## Closed as replaced by the rebuild plan

The workflow has no "Won't do" status, so these are Done with the label `superseded` and a comment naming the milestone that covers them.

| Issue | Covered by |
|---|---|
| SUITS-28 Detect EVA not started / TSS restart | M1, M2 |
| SUITS-33 HUD caution and warning | M2 |
| SUITS-34 UIA and DCU panels | M2 |
| SUITS-36 Fault flags in the banner (branch not merged; the HUD is rewritten) | M2 |
| SUITS-37 HUD reconnects automatically | M1 |
| SUITS-38 Forward position and spectrometer | M4, M7 |
| SUITS-39 2D map, breadcrumbs, pins | M4 |
| SUITS-40 Spectrometer panel | M7 |
| SUITS-41, 42 Forecast and predicted range | M5 |
| SUITS-43 Egress checklist | M3 |
| SUITS-47 Voice assistant | M6 |
| SUITS-48 Station procedures, ingress, geology log | M3, M7 |
| SUITS-49 Full mock mission and demo video | M8, M10 |
| SUITS-50 ML evaluation writeup | M5, M6 |
| SUITS-52 Seismic unit panel | M7 |
| SUITS-54 Best path avoiding keep-out zones | M4 |
| SUITS-32 Training data into pandas | M5 |
| SUITS-44, 45, 46 Isolation forest, GRU, autoencoder | Dropped for the one-month scope. Anomaly detection is a stretch item. |
| SUITS-51 Second crew member on the map | Stretch |
| SUITS-53 Walking speed model | Dropped; M4 uses measured speed |
| SUITS-29, 30, 35 Rotation reviews, docs cleanup | The way of working changed: AI builds, we review. Walkthrough notes replace rotation reviews. |

## Epics

| Epic | Change |
|---|---|
| SUITS-1 Telemetry | Keep. Holds M1, M2 |
| SUITS-2 Virtual Hardware | Close. Replaced by the fake TSS and scenario driver (M1, M3) |
| SUITS-3 HUD | Keep. Holds M3, M4, M7 |
| SUITS-4 AI/ML | Keep. Holds M5, M6 |
| SUITS-5 Showcase | Keep. Holds M8, M9, M10 |

## Created

SUITS-55 to SUITS-64 are M1 to M10. SUITS-65 to SUITS-68 are the Fable reviews for M1, M5, M6 and M8.

Ten stories, one per milestone, titled as in `docs/plan/README.md` ("M1 Walking skeleton" … "M10 Passthrough tuning and walk-through demo"). Description: the goal line and a link to the milestone file. Four review tasks: "Fable review: M1 patterns", "…M5 evaluation method", "…M6 guardrails", "…M8 whole system".

## Sprints

Old sprints were left alone: Sprint 2 is still active and Sprints 3 to 6 are still planned, but they now hold only closed issues. Complete or delete them in Jira when you like. Created four one-week sprints, not started, no dates, matching the calendar in `docs/plan/README.md`: Week 1 (M1, M2), Week 2 (M3, M4, M5), Week 3 (M6, M7, M8), Week 4 (M9, M10). Move M9 and M10 out if the headset is late.

## Git housekeeping (Kenny and Vlad do this themselves)

- Push `plan-rebuild` and merge it into `main`. It contains the SUITS-31 commits plus the plan files.
- Leave `SUITS-36-fault-flags` unmerged; the HUD is rewritten in M1–M2. Delete it and the other merged feature branches when you like.
