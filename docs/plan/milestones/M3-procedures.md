# M3 — Procedures: egress and ingress

**Goal:** the HUD walks the astronaut through egress and ingress, checks each step from live switch states and suit values, and catches wrong switches. A scenario driver can play a whole procedure. NASA requirement 3a (egress and ingress part).

**Builder:** Opus 5.5 (Sonnet subagent for the procedure data files). **Fable review:** no.

**Read first:** `docs/walkthroughs/M2.md`; mission description Appendix A (page 10) and page 5; notes `tss-driving-the-sim`, `tss-dcu-switch-meaning`.

## Scope

1. **Procedure data** (`data/procedures/egress.yaml`, `ingress.yaml`). Each step: `text`, `actor` (UIA, DCU or HUD), and either `done_when` (a condition) or `manual: true`; optional `progress` (a value and its target, for wait steps) and `expect_switch`.
   - Egress follows FY27 Appendix A: connect and start depress; vent tanks below 10 psi; fill primary, then secondary; end depress at suit pressure 4; final switch checks; disconnect.
   - Add the coolant fill from NASA's 2025-26 timeline after the oxygen fill (DCU PUMP open, UIA water supply open, wait for coolant above 95%, close). Appendix A leaves it out, but the TSS starts with coolant at 0, which is a warning. Mark these steps in the file as ours.
   - Use 2950 psi, not 3000, for "tank full" (see `scope.md`). Use a tolerance for "pressure = 4". Keep thresholds in the data file.
   - Ingress follows NASA's 2025-26 timeline (`vendor/TSS2027/documents/procedures/ev-team-procedure-timeline.pdf`), including the coolant drain below 5%.
   - Remember every DCU switch starts in the secondary position (`tss-dcu-switch-meaning`).
2. **Conditions:** a small data-only language, no `eval`: `{switch: uia.o2_vent, is: OPEN}`, `{value: oxy_pri_pressure, op: ">", than: 2950}` (switch names as in the contract's `dcu` and `uia`; value names are keys of `suit.values`), `all: [...]`, `any: [...]`.
3. **Engine** (`core/procedures.py`): start a procedure by command; steps complete in order; a `done_when` step completes after its condition holds for 1 s; a manual step completes on `next_step`; a switch change that is not the current step's raises a caution "unexpected switch" and does not advance.
4. **Mission phase** in `eva.phase`: `pre_egress → egress → traverse → poi → return → ingress → done`. In M3 it is derived from procedures only.
5. **Scenario driver** (`sim/driver.py`, `data/scenarios/*.yaml`, `npm run scenario`): timed actions (start EVA, set switch, set value, set fault, set position, set rock), a speed factor, and two targets: the fake TSS, or a real TSS through the legacy commands and its web endpoints.
6. **Panels:** procedure panel (current step large, next step small, step count, progress bar for wait steps); the DCU/UIA panel highlights the switch to use.
7. **Input:** `next_step`, `prev_step`, `start_procedure`, added to both binding tables.

## Acceptance

Backend (pytest)
1. Every procedure file passes schema validation, and every switch and value it names exists in the contract.
2. Condition tests: each operator, `all`, `any`, unknown names rejected at load time.
3. The egress file's switch order equals a table taken from Appendix A plus the coolant fill (asserted step by step). After a scripted correct egress, the coolant and suit-pressure values are not at warning level.
4. Scripted correct egress: every step completes in order and `eva.phase` ends as `traverse`. During a fill step `progress` rises from 0 to 1.
5. A wrong switch raises the caution and the step index does not change. A manual step advances only on `next_step`.
6. Ingress: same checks; `eva.phase` ends as `done`.
7. Driver: `egress_nominal` against the fake TSS at 20× finishes in under 30 s of real time with the procedure complete.

Client (vitest)
8. Procedure panel view model: first step, wait step with progress, last step, no active procedure.

End to end (Playwright)
9. Play `egress_nominal`; the step text on `window.__hud` changes through the expected sequence; screenshot at a wait step.
10. Emulated headset: `next_step` from an emulated controller button advances a manual step.

Manual, optional
11. The driver completes egress against a real TSS in WSL. Record the result in the walkthrough.
