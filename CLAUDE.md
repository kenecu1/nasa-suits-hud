# NASA SUITS HUD — guide for builder sessions

A spacesuit heads-up display for a simulated lunar spacewalk. Final target: Meta Quest 3S in passthrough (WebXR). Development target: a laptop browser. Kenny and Vlad review and steer; AI sessions build.

## Start here

1. `docs/plan/README.md` — status table and build order.
2. Your milestone file in `docs/plan/milestones/`. It is your spec. Do not read the other milestone files unless yours links to them.
3. `docs/plan/architecture.md` — read once.
4. `docs/notes/README.md` — the index. Open only the notes for your area.

## Rules that protect the design

- **TSS knowledge stays in one place.** Only `backend/suits/tss/` (and the fake in `backend/suits/sim/`) knows TSS ports, packet layouts and field names. Everything else uses `TssSnapshot`.
- **Logic in the backend, drawing in the client.** The client formats and draws the `state` message. It computes no mission logic.
- **One contract.** `backend/suits/contract.py` is the source of truth. After changing it run `npm run contract`. Never edit `client/src/contract.gen.ts` by hand.
- **The HUD is WebGL only.** No HTML inside the headset view. Each panel is a pure view-model function (`client/src/hud/*.vm.ts`, unit tested) plus a thin component in `client/src/scene/`.
- **Sizes and colours come from `client/src/theme.ts`.** No literal colours or font sizes in components.
- **Every user action is an intent** (`client/src/input/intents.ts`) that becomes a `command` message. Do not bind keys or controller buttons inside components.
- **Data, not code:** ranges, alerts, procedures, site and map, scenarios and voice intents live in `data/`.
- **No automated test may need** the real TSS, the headset, a microphone, the network or an API key. Use sim mode, recordings, fixtures and the fake language model. Downloads happen only in `npm run setup`.
- Secrets go in `.env` (gitignored). Never commit `ANTHROPIC_API_KEY`.

## Commands (run from the repo root, PowerShell)

M1 creates these unless a milestone is named. Whoever adds or changes a command updates this table.

| Command | What it does |
|---|---|
| `npm run setup` | Create `.venv`, install Python and Node packages and Playwright browsers |
| `npm run dev` | Backend in sim mode + client. Open `http://localhost:5173` |
| `npm run check` | Everything: ruff, pytest, contract drift, tsc, eslint, vitest, Playwright |
| `npm run check:fast` | Same without Playwright |
| `npm run contract` | Regenerate TypeScript types from the Python contract |
| `npm run tss:smoke` | Talk to a real TSS for 5 s and print decoded data (needs `TSS_HOST`); `-- --record` saves a recording |
| `npm run scenario -- <name>` | (M3) Play `data/scenarios/<name>.yaml` against the running backend's TSS source |
| `npm run ml:train`, `npm run ml:evaluate` | (M5) Build the dataset and model; write `docs/ml/forecast-report.md` |
| `npm run eval:voice` | (M6) Voice evaluation against the real API; needs `ANTHROPIC_API_KEY` |
| `npm run demo` | (M8) Sim mode plus the full mission scenario |

Backend modes, set with `SUITS_MODE`: `sim` (default, built-in fake TSS), `replay` (`SUITS_RECORDING=<file>`), `live` (`TSS_HOST`, `TSS_TEAM`).

## Testing

- **Without the TSS (the normal case):** `npm run check`. The backend runs against the fake TSS or a recording.
- **With the real TSS (smoke only):** build and run it in WSL (`docs/notes/tss-build-and-run.md`), assign the laptop's IP to a team in the TSS web UI, then `npm run tss:smoke`, then `SUITS_MODE=live npm run dev`.
- **Headset view without a headset:** the same scene runs in an emulated WebXR session. Playwright does this in `e2e/xr/`. By hand: `npm run dev` and use the emulator panel on the page.
- HUD content is not in the DOM. Tests read `window.__hud` (the current view models) and compare screenshots.
- **Screenshots:** baselines are committed for Windows only and compared with `maxDiffPixelRatio: 0.02`. CI (Linux) runs the same tests with snapshot comparison off and uploads the screenshots. Assertions on `window.__hud` are the real check; screenshots catch layout accidents.
- **NASA's TSS source** is in `vendor/TSS2027` after setup (pinned commit in `backend/suits/tss/VERSION`).

## Before you call a milestone done

1. Every acceptance criterion in the milestone file passes, and `npm run check` is green. Put the summary lines in the walkthrough.
2. If a criterion cannot be met, say so plainly to the user and in the walkthrough. Do not weaken the test.
3. `docs/walkthroughs/M<n>.md` exists: one page with what was built, how data flows through it, three things to try, and three questions Kenny and Vlad should be able to answer.
4. New lessons are in `docs/notes/` (one per file, summary on line one, index updated). Wrong notes are fixed.
5. The status table in `docs/plan/README.md` is updated.
6. If the milestone file asks for a Fable review, stop and tell the user. Do not start the next milestone.

## Git

- One branch per milestone, named `m<n>-<slug>` (for example `m1-walking-skeleton`). If a Jira story exists for it, prefix its key: `SUITS-<number>-m<n>-<slug>`.
- **Commit locally only.** Kenny and Vlad push to GitHub and open pull requests themselves. Never run `git push`, never open a pull request.
- Commit as the configured git user. Do not add `Co-Authored-By` or "Generated with" lines to commits.
- Never delete branches or rewrite pushed history. Jira: move the milestone's story to In Progress when you start and to Done when the user accepts it; ask before any other Jira change.
- Small commits with plain messages.

## Budget

Usage is tight. Do bulk reading and searching in Sonnet subagents and keep only their conclusions. Do not re-read a large file you have already summarised. Look up current library docs for `@react-three/xr`, `@react-three/uikit` and `iwer` instead of trusting memory; these change often.
