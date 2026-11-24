@react-three/uikit wraps text at word breaks by default, and a fixed-height panel squeezes its rows until they overlap; set `wordBreak="keep-all"` on the panel and `flexShrink={0}` on rows.

Found in M2 (2026-11-24) with @react-three/uikit 1.0:
- "0.100 psi/min" split over two lines and read as two values. `wordBreak="keep-all"` (uikit's no-wrap, `NowrapWrapper` in `@pmndrs/uikit/dist/text/layout/measure.js`) is inherited, so `scene/PanelAt.tsx` sets it once on each panel's root.
- A panel with a fixed `height` shrinks its children to fit, so rows drew on top of each other. Rows now have `flexShrink={0}` and the panel boxes in `hud/layout.ts` allow about 1.2 × font size per line plus gaps and padding.
- Text sizes: at 24 dmm (28.8 panel pixels at 1.2 m) a capital is about 17–19 px wide, so a 470 px side panel holds about 25 characters in a row. Keep labels short and let the group title give the context.
- Open the e2e screenshots after a layout change: wrapping and overlap do not show in `window.__hud`.
