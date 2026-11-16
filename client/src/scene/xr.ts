// The WebXR session setup. One store for the whole page.
import { createXRStore } from "@react-three/xr";

/**
 * On localhost, in a browser without WebXR, @react-three/xr can inject an emulated Quest 3 with
 * a control panel (for trying the headset view by hand). `?emulator=off` turns that off: the
 * end-to-end tests use it, and install their own emulator when they need one.
 */
function emulatorWanted(): boolean {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("emulator") !== "off";
}

export const xrStore = createXRStore({
  // No synthetic room: it would be downloaded from the internet.
  emulate: emulatorWanted() ? { type: "metaQuest3", syntheticEnvironment: false } : false,
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
