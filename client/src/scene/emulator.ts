// The emulated headset for trying the headset view by hand on the laptop (dev server only).
//
// @react-three/xr has this built in, but with iwer 2.8 its emulator no longer installs in
// Chromium: the browser has a navigator.xr of its own (one that supports no headset), and iwer
// now leaves a native one alone unless forced. So the page installs iwer itself, forced.
// See docs/notes/xr-emulation-headless-works.md.

/** `?emulator=off` keeps the emulator out; the end-to-end tests use it and install their own. */
function emulatorWanted(): boolean {
  const local = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  return local && new URLSearchParams(window.location.search).get("emulator") !== "off";
}

/** Install an emulated Quest 3 with its control panel, unless a real AR device is there. */
export async function startDevEmulator(): Promise<void> {
  if (!emulatorWanted()) return;
  const realDevice = (await navigator.xr?.isSessionSupported("immersive-ar")) ?? false;
  if (realDevice) return;

  const [{ XRDevice, metaQuest3 }, { DevUI }] = await Promise.all([import("iwer"), import("@iwer/devui")]);
  const headset = new XRDevice(metaQuest3);
  headset.installRuntime({ forceInstall: true });
  headset.installDevUI(DevUI);
  console.info("Emulated Quest 3 installed. Press Enter AR; add ?emulator=off to the address to leave it out.");
}
