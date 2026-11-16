// The WebXR session setup. One store for the whole page.
import { createXRStore } from "@react-three/xr";

export const xrStore = createXRStore({
  // The library's own emulator is off: the page installs one itself (scene/emulator.ts).
  emulate: false,
  // The Enter AR button is the one way in.
  offerSession: false,
  // M1 has no input in the headset. Controller and hand models would be downloaded and drawn.
  controller: false,
  hand: false,
  gaze: false,
  transientPointer: false,
  screenInput: false,
  // The HUD needs only head tracking. Ask for nothing else.
  domOverlay: false, // the Quest Browser has none (docs/notes/quest-no-dom-overlay.md)
  anchors: false,
  handTracking: false,
  layers: false,
  meshDetection: false,
  planeDetection: false,
  hitTest: false,
});
