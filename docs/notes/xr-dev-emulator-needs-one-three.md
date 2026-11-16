The emulator control panel (`@iwer/devui`) crashes every frame unless Vite is told to use one copy of three.js (`resolve.dedupe: ["three"]`), and the built-in emulator of `@react-three/xr` does not install in Chromium at all.

Found in M1 (2026-11-16) with `@react-three/xr` 6.6.32, iwer 2.8.0, `@iwer/devui` 1.1.2, three 0.187.

- `@react-three/xr`'s `emulate` option calls `installRuntime()` without `forceInstall`, so with iwer 2.8 it does nothing in Chromium (see [xr-emulation-headless-works](xr-emulation-headless-works.md)). The page installs the emulator itself in `client/src/scene/emulator.ts` (dev server only, localhost only, off with `?emulator=off`).
- `@iwer/devui` depends on three `^0.165` and gets its own nested copy, but it shares `@pmndrs/handle` with the app, which uses the app's three 0.187. Mixed objects fail with `material.onBuild is not a function` inside `DevUI.render`, on every frame, and that stops the XR frame loop: the session starts but the HUD is never drawn.
- Fix: `resolve.dedupe: ["three"]` in `client/vite.config.ts`. The console warning "Multiple instances of Three.js being imported" is the early sign.
- Check after any upgrade of three, `@react-three/xr` or iwer: `npm run dev`, open the page, press Enter AR, and look for the panel next to the controller gizmos.
