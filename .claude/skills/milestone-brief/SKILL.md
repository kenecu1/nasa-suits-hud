---
name: milestone-brief
description: Before a milestone is built, explain its design to Kenny and Vlad so they understand and can steer it. Writes docs/briefs/M<n>.md with diagrams, the data flow, design choices with alternatives, open decisions and prediction questions. Writes no code. Use when the user says "brief M<n>", "explain M<n> before we build it" or "what will M<n> do".
---

# Milestone brief (before building)

The aim is for Kenny and Vlad to understand **how the milestone will work before any code exists**: which parts change, how data moves through them, and why the design is this way and not another. They need the big picture, the interactions between components and files, and the reasons behind the choices. They do not need every function or library detail.

You are explaining and helping them decide. **Do not write or change code. Do not create branches.**

## Inputs (read only these)

1. `docs/plan/milestones/M<n>-*.md`: the spec.
2. `docs/plan/architecture.md`
3. Files the milestone's "Read first" line names, plus `docs/briefs/M<n-1>.md` and `docs/walkthroughs/M<n-1>.md` if they exist (they show what already exists).
4. Notes from `docs/notes/README.md` for this area only.

If you need to know what code exists today, send a Sonnet subagent and keep only its conclusions (this follows the budget rule in CLAUDE.md).

## Output: `docs/briefs/M<n>.md`

Keep it to about two printed pages. Use plain words and short sentences. Diagrams are Mermaid, so GitHub renders them.

1. **In one paragraph.** What the wearer or operator can do after this milestone that they could not do before.
2. **Where it sits.** A Mermaid `flowchart LR` of the whole system (TSS → tss adapter → core → state message → client view models → scene, plus input → intents → command). Highlight new or changed parts with `classDef new fill:#2d6,color:#000`. Leave untouched parts grey.
3. **One event, end to end.** A Mermaid `sequenceDiagram` for one concrete event, chosen to cross the most boundaries (for M2: "fan speed drops out of range → banner shows a warning with its action → wearer acknowledges"). Under it, add a numbered list giving one line per arrow: what is sent, its shape, and which folder handles it.
4. **Contract changes.** The fields added to `state`, `command` or other messages, with one example JSON snippet.
5. **Files by responsibility.** Group by layer (backend tss / sim / core, contract, client hud / scene / input, data). Give each file one line saying what it is responsible for and what it must never do, not how it works.
6. **Design choices.** A table with the columns Choice | Chosen | Alternative | Why this one. Include 4–6 choices, taken from the milestone and architecture.md, such as full state vs deltas or flapping thresholds.
7. **Open decisions: your call.** Things the spec leaves open or where a reasonable person might disagree. For each one, give two options, the trade-off and your recommendation. Write "none" if there are none. Do not invent decisions to fill this section.
8. **Learn these, skip those.** List the 3–5 concepts worth understanding deeply for this milestone, each with a 2–3 sentence explanation (for example hysteresis, dmm text sizing, view models). Then give one line naming what is safe to skip (library APIs and similar).
9. **Can look right while being wrong.** List 2–3 failure modes a demo would not show, and say which acceptance test catches each one.
10. **Predict before you read the code.** Write 4–5 questions that make them reason about the design, not recall names. Examples: "Link drops for 3 s: what does every panel show and why?" or "Where would you add a new alert, and which files would you not touch?" Put each answer in a `<details><summary>Answer</summary>…</details>` block.
11. **Decisions taken.** Leave this section empty under the heading. It is filled after the discussion.

## Interactive companion: `docs/briefs/M<n>-explorer.html`

Kenny and Vlad want as much interactivity as possible. After the brief, build one self-contained HTML page (no build step, no external data) and publish it as an Artifact. Link it at the top of the brief. Use `docs/briefs/M1-explorer.html` as the pattern: tabs, real data from the notes and `data/`, and plain words. Pick 5–8 instruments that fit this milestone, for example:
- a clickable system map with lenses (what changes, what is pure, what runs in the headset)
- an event stepper: a sequence diagram revealed one message at a time, showing the real payloads and "if this hop is built badly"
- a simulator of the milestone's core logic, such as alert hysteresis (M2), a procedure state machine (M3), bearing and route geometry (M4), forecast intervals (M5), or the guardrail check on spoken numbers (M6)
- a failure simulator: break inputs and watch what each layer notices
- self-checks: a "where does this job live?" drill, "which files change if…", and the prediction questions with written answers kept in browser storage

Label every simulation as a model of the design, not the real code. Commit the page with the brief.

## After writing

1. In chat, give a short summary and the link. Ask them to read the diagrams first and try the prediction questions before opening the answers.
2. Discuss with them. Answer questions with diagrams or traced examples rather than long prose. If they want to see something interactively (a state machine, a geometry problem), offer an Artifact page.
3. When they decide the open points, write the outcomes under **Decisions taken**. Builder sessions read this section. If a decision changes the spec, propose the exact edit to the milestone file and make it only after they say yes.
4. Commit only `docs/briefs/M<n>.md` (plus an approved milestone edit), with a plain message like "Brief for M2". Commit locally only and never push.
