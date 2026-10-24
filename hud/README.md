# HUD

React + TypeScript spacesuit HUD for our NASA SUITS 2027 style project.

## Setup
1. Install dependencies:
```
   npm install
```
2. Copy the config template, then set the bridge address if yours is different:
```
   copy .env.example .env
```
3. Start the HUD:
```
   npm run dev
```

## Config
The bridge address lives in **one place**: `VITE_BRIDGE_URL` in `.env`.
`src/config.ts` reads it and stops the app with a clear error if it's missing.
Never hardcode the address in a component; import `config` instead.

## Folder layout
```
src/
  main.tsx        starts React
  App.tsx         renders the layout
  config.ts       reads settings from .env
  index.css       dark theme colors
  layout/         HudLayout: where each panel sits (CSS Grid)
  panels/         one file per HUD region
```

## Adding a new panel
1. Create `src/panels/YourPanel.tsx`
2. Import it in `src/layout/HudLayout.tsx` and wrap it in `<div className="area-yours">`
3. Add `yours` to `grid-template-areas` and a `.area-yours` rule in `HudLayout.css`

Panels never set their own position. Layout decides where things go.

## Design
See [docs/hud-layout.md](../docs/hud-layout.md) for the layout decisions and reasons.