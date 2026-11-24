Read controller buttons from `session.inputSources[i].gamepad.buttons` directly: @react-three/xr's controller state fetches its input profile from a CDN, which tests may not do.

Verified in M2 (2026-11-24) with @react-three/xr 6.6 and iwer 2.8:
- `useXRInputSourceState("controller", "right")` and `useXRControllerButtonEvent` depend on a controller layout loaded by `XRControllerLayoutLoader`, which fetches `profilesList.json` and a profile from a CDN (`@pmndrs/xr/dist/controller/layout.js`). CLAUDE.md forbids network in tests, and the state is `undefined` until the download finishes.
- Raw WebXR works offline: `gl.xr.getSession().inputSources` in `useFrame`, then `gamepad.buttons[index].pressed`. On the right Meta Quest Touch controller (xr-standard mapping) A is index 4 and B is index 5; left X and Y are 4 and 5 on the left hand. Fire on the frame a button goes down, not while held (`client/src/input/buttonPresses.ts`).
- This works with `controller: false` in `createXRStore` (no controller model is drawn, nothing is downloaded).
- In a test, press a button on the iwer device: `headset.controllers.right.updateButtonValue("a-button", 1)`, wait a few frames, then set it back to 0 (`e2e/xr/headset.spec.ts`).
