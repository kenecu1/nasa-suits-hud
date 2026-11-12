The Quest Browser does not reliably show HTML inside an immersive WebXR session (no DOM overlay), so every HUD element must be drawn in WebGL.

Source: web research 2026-11-12 (Meta forum reports, newest May 2025). Not checked on a device.

- Do not build HUD panels as HTML/CSS. Use three.js objects (we use `@react-three/uikit` for flexbox-style panels and text).
- HTML is fine for things outside the headset view: the operator page, the start screen with the "Enter AR" button, debug tools.
- Because the HUD is WebGL on the laptop too, the laptop and the headset show the same thing. Tests cannot query HUD text through the DOM; they read the view model exposed on `window.__hud` and compare screenshots.
