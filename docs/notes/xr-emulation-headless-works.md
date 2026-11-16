A WebXR `immersive-ar` session runs in headless Chromium with the `iwer` emulator, but `installRuntime` must be forced, because Chromium already has a `navigator.xr` of its own.

Proved in M1 (2026-11-16): `e2e/xr/headset.spec.ts` passes headless on Windows with Playwright 1.65, iwer 2.8.0, `@react-three/xr` 6.6.32. No fallback was needed. (This note was `xr-emulation-headless-unverified` before M1.)

- Chromium on localhost has a native `navigator.xr` that supports no headset. Since iwer 2.8, `XRDevice.installRuntime()` leaves a native runtime alone and only warns. Call `installRuntime({ forceInstall: true })`. Without it, Enter AR fails with "The specified session configuration is not supported" (Chromium's message, not iwer's).
- The test installs iwer with `page.addInitScript({ path: "node_modules/iwer/build/iwer.min.js" })` (global `IWER`), then `new IWER.XRDevice(IWER.metaQuest3)`. The head is turned with `device.quaternion.set(x, y, z, w)`.
- WebGL in headless Chromium needs `--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist` (`playwright.config.ts`). Software rendering also makes screenshots the same on every Windows machine.
- three.js copies the head pose onto the normal scene camera on every render, so code that reads `state.camera` in `useFrame` follows the head with no XR-specific code.
- Turn off what the HUD does not need in `createXRStore` (`scene/xr.ts`): the default controller and hand models are downloaded from the internet, and `emulate` would load a synthetic room from unpkg.
- Tests cannot see WebGL content. They read `window.__hud.view`, which is measured from the renderer's real per-eye cameras (`scene/ViewProbe.tsx`).
