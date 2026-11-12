# Plan

Written 2026-11-12. This replaces the earlier plan in Jira (Sprints 0–6) and the stack decision in `docs/decisions.md`.

## The goal

In about one month: one of us wears a Quest 3S in a dim room, walks a scaled-down lunar mission (egress, walk to a point of interest, a science task, walk back, ingress) guided by the HUD and a voice assistant, while the other operates NASA's TSS. We record it as a first-person video. A complete laptop demo exists before the headset arrives and is the fallback.

## The decisions in five lines

1. **One web app, drawn in WebGL** (React + three.js through `@react-three/fiber`, `@react-three/xr`, `@react-three/uikit`). The same scene runs as a laptop page, in an emulated headset session for tests, and in the Quest Browser.
2. **A Python backend on the laptop is the only TSS client** and holds all mission logic, ML and speech. The headset is a thin display that connects to the laptop.
3. **One TSS adapter.** Today it speaks two TSS dialects at once. When NASA changes the protocol, only the adapter changes.
4. **Everything runs without the TSS and without the headset:** a built-in fake TSS, recordings, a scenario driver that plays a whole mission, and an emulated headset in automated tests.
5. **AI features are measured:** a consumables forecast with an evaluation report, and a voice assistant whose numbers are checked against live data before they are spoken.

Details: [scope.md](scope.md), [architecture.md](architecture.md), [headset-risks.md](headset-risks.md).

## Milestones

Build in this order. After M2 there are two tracks that can run in parallel sessions (they touch different folders).

| # | Milestone | Needs | Builder | Fable review | Status |
|---|---|---|---|---|---|
| M1 | [Walking skeleton](milestones/M1-walking-skeleton.md): TSS → HUD panel on laptop and emulated headset | — | Opus 5.5 | **Yes, after** | not started |
| M2 | [Telemetry, caution and warning, low-light design](milestones/M2-telemetry-alerts.md) | M1 | Opus 5.5 | no | not started |
| M3 | [Procedures: egress and ingress](milestones/M3-procedures.md) (track A) | M2 | Opus 5.5 | no | not started |
| M4 | [Navigation](milestones/M4-navigation.md) (track A) | M3 | Opus 5.5 | no | not started |
| M5 | [Forecast and predicted range](milestones/M5-forecast.md) (track B) | M2 | Opus 5.5 | **Yes, evaluation method** | not started |
| M6 | [Voice assistant](milestones/M6-voice.md) (track B) | M2 | Opus 5.5 | **Yes, guardrails** | not started |
| M7 | [Science tasks at points of interest](milestones/M7-science.md) | M3, M4 | Sonnet 5.5 | no | not started |
| M8 | [Full mission rehearsal on the laptop](milestones/M8-rehearsal.md) | M3–M7 | Opus 5.5 | **Yes, whole system** | not started |
| M9 | [Headset bring-up](milestones/M9-headset-bringup.md) | M8 + headset | Opus 5.5 | no | waiting for headset |
| M10 | [Passthrough tuning and walk-through demo](milestones/M10-headset-demo.md) | M9 | Opus 5.5 | only if position mapping fails | waiting for headset |

Jira: M1 to M10 are SUITS-55 to SUITS-64, in order. The Fable reviews for M1, M5, M6 and M8 are SUITS-65 to SUITS-68.

No milestone needs Fable 5.2 to build it. Fable is worth its cost at the four review points: M1 sets the patterns every later milestone copies, M5 and M6 can look right while being wrong (data leakage, ungrounded answers), and M8 is the last check before headset time is spent.

Sonnet 5.5 also does the mechanical parts inside other milestones (wiring all telemetry fields in M2, procedure data files in M3) as subagents.

## Suggested calendar

| Week | Work |
|---|---|
| 1 | M1, Fable review, M2 |
| 2 | M3 then M4 (track A) alongside M5 (track B) |
| 3 | M6 alongside M7, then M8 and the laptop demo video |
| 4 | M9 and M10 if the headset is here; otherwise stretch items |

If the headset is late, the project is "laptop complete" after M8, and M9–M10 take two or three sessions when it arrives. Nothing else waits for them.

## Cut lines if time runs short

In this order: best-path planner in M4 (keep straight-line bearing and breadcrumb backtrack), payload panels in M7 (keep the spectrometer), free-form questions in M6 (keep fixed intents). Do not cut M8.

## Stretch (only after M8)

Early-warning anomaly detection; a simulated second crew member on the map; a 3D terrain view from `lunar.obj`; a wake word instead of push-to-talk; an after-mission report generated from the log.

## Other files

- [jira-proposal.md](jira-proposal.md) — what was closed, changed and created in Jira.
- [kickoff-m1.md](kickoff-m1.md) — the message to paste into the first builder session.
- `docs/notes/` — lessons, one per file.
- `docs/reference/` — NASA's FY27 mission description.
