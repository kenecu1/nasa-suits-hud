# Scope

We are not in the challenge. NASA's requirements are a guide to what a good HUD does. Source: `docs/reference/fy27-nasa-suits-mission-description.pdf` (requirements on page 9, tasks on pages 5–8, sample egress procedure in Appendix A).

## NASA requirements

| NASA requirement | Decision | Milestone | Why |
|---|---|---|---|
| 1a Show the astronaut's suit and biomedical data | Adopt | M2 | Core of any HUD |
| Show suit, DCU, UIA, spectrometer, camera and payload data "at any time" (p7) | Adopt, camera shows "no data" | M2, M7 | The TSS sends nothing for the camera yet |
| 2a 2D map | Adopt | M4 | |
| 2b Map shows live assets such as other crew | Change | stretch | The TSS has no second-crew data. The contract has a slot for it; a simulated crew member is a stretch item |
| 2c 3D map (may) | Drop | stretch | Optional for NASA, costly, little demo value |
| 3a Correct procedures for each station | Adopt | M3, M7 | Egress and ingress check themselves from switch states. Station tasks are checklists with live device data where the TSS has it |
| 3b Voice assistance in natural language | Adopt | M6 | Also our main AI feature |
| 4a Breadcrumbs, backtrack to the lander | Adopt | M4 | |
| 4b Best-path navigation (should) | Adopt, first to cut | M4 | Shortest safe path around keep-out zones |
| 4c Navigation aids to points of interest | Adopt | M4 | Bearing, distance, time to arrive |
| 4d Predicted maximum range from life-support use | Adopt | M5 | Our main ML feature |
| 5a Drop a pin at any time | Adopt | M4 | By key, controller or voice |
| 6a, 6b Caution and warning for off-nominal suit or biometric values | Adopt | M2 | |
| Head-mounted displays must be passthrough AR (p3) | Adopt | M9, M10 | Quest 3S, WebXR `immersive-ar` |
| Guardrails against hallucination, short spoken answers (p4) | Adopt, and measure it | M6 | |
| Peripheral device rules (p9) | Drop | — | We build no hardware |
| Astronaut camera photos; computer vision (optional) | Drop | — | Web pages cannot read the Quest camera. A "photo" is a log entry with place and time |
| Physical tasks: collect samples, deploy the camera, place markers | Change | M7 | Checklist steps the wearer confirms; nothing physical |
| Physical UIA and DCU panels | Change | M3 | The operator flips switches in the TSS web page, or the scenario driver does |
| NASA's location system | Change | M4, M10 | Position comes from the TSS when a script feeds it, or from headset tracking scaled onto the map |
| Test week rules, design review, team size, paper | Drop | — | Not taking part |

Egress thresholds: Appendix A says "above 3000 psi", but the TSS tank tops out just under 3000 and its range table has 3000 as the maximum. We use 2950 (as NASA's 2025-26 procedure did). Thresholds live in the procedure data files. Appendix A also leaves out the coolant fill; we add it from NASA's 2025-26 procedure because the TSS starts with an empty coolant tank.

## What we add

| Addition | Milestone | Why |
|---|---|---|
| Sim mode: built-in fake TSS with the TSS's telemetry behaviour | M1, M5 | Build, test and demo with nothing else running; fast training data |
| Scenario driver: plays a whole scripted mission | M3 | End-to-end tests, repeatable demos, one-person demos |
| Record and replay of real TSS traffic | M1 | Regression tests when NASA changes the protocol |
| Turn-back advisor: alert when the way home is about to exceed what the suit can support | M5 | Makes the range prediction actionable |
| Low-light theme with tested text size and contrast | M2 | Testing is in low light through video passthrough |
| Live tuning page: change sizes and colours from the laptop while someone wears the headset | M8 | Makes headset tuning fast |
| Evaluation reports for the forecast and the voice assistant | M5, M6 | Portfolio evidence that the AI features work |
| Walkthrough note per milestone | all | So we can explain the system |

## Out of scope

Custom hardware, multi-user sessions, a mission-control app, native (Unity) builds, cloud hosting, accounts.

## The project is done when

1. `npm run check` is green, including a full scripted mission in the emulated headset (M8).
2. A laptop demo video exists (M8).
3. A first-person headset video of a walked mission exists (M10), or, if the headset never arrives, item 2 stands as the result.
4. The README shows the architecture, the two evaluation reports and the videos.
