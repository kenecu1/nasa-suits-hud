---
name: milestone-debrief
description: After a milestone is built, check that Kenny and Vlad understand what was actually built, compared with what the brief said would be built. Adds an "After build" section to docs/briefs/M<n>.md, traces one real event through the actual files, runs a teach-back in chat and adds 2–3 exercises. Use when the user says "debrief M<n>", "quiz us on M<n>" or "walk us through what M<n> built".
---

# Milestone debrief (after building)

The brief explained the plan. This skill checks that the plan in their heads matches the code that now exists, and closes the gaps. It is about understanding, not reviewing. Report bugs you notice, but do not fix them here.

## Inputs

1. `docs/briefs/M<n>.md` (the plan and the decisions taken) and `docs/walkthroughs/M<n>.md` (the builder's account).
2. The milestone's changes: `git diff --stat <base>...m<n>-*` for the shape. Send a Sonnet subagent to read the key files and return the real path of the brief's end-to-end event as `file:line` hops. Do not read the whole diff yourself.

## Add to `docs/briefs/M<n>.md`, under `## After build`

1. **Plan vs reality.** List what differs from the brief and why (file names, an extra component, a changed choice). If the structure differs, redraw the flowchart. Otherwise write "matches the brief".
2. **The event, in real code.** Repeat the brief's sequence diagram, then give a numbered trace with one line per hop: the `file:line` link, then what happens there in plain words. This is the map for reading the code. Keep it under about 12 hops.
3. **Exercises.** Write 2–3 exercises, each answerable in about 10 minutes. Use a mix of:
   - *Trace:* "Follow `<field>` from the TSS packet to the pixel. Name each file."
   - *Change it:* "Add a new alert for X. List every file you would touch, and the ones you would not."
   - *Break it:* "What happens if Y? Run `<command>` to check."
   - For math-heavy milestones (M4 navigation, M5 forecast), add a small problem to work by hand, such as a bearing between two points or a confidence interval from 5 numbers.
   Put each answer in a `<details>` block.

## Teach-back in chat (the most important part)

Before showing the trace, ask one of them to explain, in their own words, how the end-to-end event works. Then:
- Say what was right, briefly.
- Name each gap or misconception, and correct it with a pointer to the exact hop in the trace.
- Ask one follow-up "why" question about a design choice ("why does the client not decide alert severity?").

Keep it a conversation. Do not lecture. If a gap shows the docs were unclear, fix the brief or add a note in `docs/notes/` (one lesson per file, index updated).

## Finish

Commit the updated brief and any notes locally with a plain message like "Debrief for M2". Never push.
