# HUD

React + TypeScript spacesuit HUD for our NASA SUITS 2027 style project.

## Setup
1. Install dependencies:
   ```
   npm install
   ```
2. Copy the config template, then edit it if needed:
   ```
   copy .env.example .env
   ```
3. Start the HUD:
   ```
   npm run dev
   ```

## Config
All settings live in `.env`, read only by `src/config.ts`.

| Setting | Meaning |
|---|---|
| `VITE_BRIDGE_URL` | Bridge WebSocket address, e.g. `ws://localhost:8000/ws` |
| `VITE_USE_MOCK` | `true` = fake data, no bridge needed. `false` = connect to the bridge |

With `VITE_USE_MOCK=false`, start the bridge first (see `bridge/README.md`).
Replay mode works without the TSS. Restart `npm run dev` after changing `.env`.

Never hardcode the bridge address in a component; import `config` instead.

## Folder layout
```
src/
  main.tsx        starts React
  App.tsx         renders the layout
  config.ts       reads settings from .env
  index.css       dark theme colors
  layout/         HudLayout: where each panel sits (CSS Grid)
  panels/         one file per HUD region
  telemetry/      types, mock data, and the useTelemetry hook
```

## How data reaches the screen
```
bridge → WebSocket → useTelemetry (handle) → HudLayout → panels
```
`useTelemetry` is called **once** in `HudLayout` and passed down, so every panel shows the same moment.

## Warnings
The banner shows the most serious problem first:
1. Contract version mismatch
2. Bridge offline (no message for 3 seconds)
3. TSS offline or sending bad data
4. EVA not started
5. All systems nominal

When the bridge or TSS is down, values stay on screen but fade to show they're stale.

## Adding a new panel
1. Create `src/panels/YourPanel.tsx`
2. Import it in `src/layout/HudLayout.tsx` and wrap it in `<div className="area-yours">`
3. Add `yours` to `grid-template-areas` and a `.area-yours` rule in `HudLayout.css`

Panels never set their own position. Layout decides where things go.

## Design
See [docs/hud-layout.md](../docs/hud-layout.md) for the layout decisions and reasons.
The message format is in [docs/contracts/telemetry.md](../docs/contracts/telemetry.md).