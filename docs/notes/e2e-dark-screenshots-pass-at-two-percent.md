On the mostly black HUD page, a whole new panel layout changes fewer than 2% of pixels, so `toHaveScreenshot` at `maxDiffPixelRatio: 0.02` still passes against an old baseline.

Found in M2 (2026-11-24): after M2 replaced M1's single panel with six panels, the xr test `in-session` still passed against M1's picture. `--update-snapshots` (which by default rewrites only failing baselines) left the stale one in place.

What to do:
- Treat the `window.__hud` assertions as the real check (CLAUDE.md, Testing). Screenshots only catch gross accidents.
- When a change is meant to alter the picture, refresh the affected baselines with `npm run e2e -- --update-snapshots=all -g "<test name>"`, then open each new PNG and look at it before committing.
- Delete a baseline whose test was renamed or removed: Playwright does not.
