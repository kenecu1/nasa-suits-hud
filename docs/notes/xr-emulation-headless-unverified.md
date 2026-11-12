Running a WebXR session in headless Playwright by injecting the `iwer` emulator is plausible but unproven; milestone M1 must prove it or switch to the fallback.

Source: web research 2026-11-12.

- `iwer` (Immersive Web Emulation Runtime, 2.8.x) is a pure-JavaScript WebXR runtime. `@react-three/xr` 6.x bundles it with a dev UI and injects it on localhost when the browser has no WebXR.
- Meta's Immersive Web Emulator browser extension 2.0 is for manual use. Version 1.x conflicts with the built-in emulator and must be off.
- Expected approach for tests: Playwright `addInitScript` installs `iwer` as an emulated Quest 3 before the page loads; the test clicks "Enter AR", sets the head pose through the emulator, and reads `window.__hud`.
- Headless Chromium may need `--use-gl=swiftshader` or `--enable-unsafe-swiftshader` for WebGL. Screenshots from software rendering differ from GPU ones: keep screenshot baselines per environment or use a tolerance.

**Fallback if it does not work in headless mode:** run the XR tests in headed Chromium locally only (not in CI), and keep CI on the desktop (non-XR) rendering of the same scene.

Update this note with the result from M1.
