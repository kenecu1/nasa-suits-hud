# Kickoff message for the first builder session

Paste the text below into a new Opus 5.5 session opened in this repo.

---

You are building milestone M1 of the NASA SUITS HUD in this repo. The plan is already written; do not redesign it.

Read, in this order: `CLAUDE.md`, `docs/plan/README.md`, `docs/plan/architecture.md`, `docs/plan/milestones/M1-walking-skeleton.md`, then `docs/notes/README.md` and the notes M1 lists. Do not read the other milestone files.

Then build M1 on a new local branch created from `plan-rebuild` (or from `main` if `plan-rebuild` has been merged). Name it `SUITS-55-m1-walking-skeleton`. Do parts 1–6 (backend) first and get `npm run check:fast` green before starting the client. If your context is running low at that point, stop, commit, and tell me to start a second session for parts 7–10.

Rules for this session:
- The acceptance list in the M1 file is the definition of done. Do not weaken a test to make it pass; tell me if one cannot be met.
- Look up the current docs for `@react-three/xr`, `@react-three/uikit` and `iwer` before using them.
- The emulated-headset test (item 14) is the least certain part. Prove it early with a tiny prototype. If headless does not work, use the fallback in the note and tell me.
- A real TSS may be available in WSL (`docs/notes/tss-build-and-run.md`). Ask me before starting it. Everything except item 16 must pass without it.
- Do bulk reading in Sonnet subagents. Usage is tight.
- Commit locally only. Do not push, open a pull request or delete branches; I push myself. Do not add co-author lines to commits.

When every item passes, write `docs/walkthroughs/M1.md`, update the status table in `docs/plan/README.md`, and stop. A Fable review happens before M2.
