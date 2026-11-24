// The only place that listens to headset controller buttons. Once a frame it reads the
// session's raw WebXR gamepads (no controller model or profile download needed, so tests stay
// offline) and fires the intent of every bound button that has just gone down.
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import { fireIntent } from "./dispatch";
import { newPresses, pressedButtons } from "./buttonPresses";

export function XrButtons() {
  // null: no session yet, so the first frame of a session only records what is already held
  // (the press that entered AR must not count as A or B).
  const down = useRef<ReadonlySet<string> | null>(null);
  useFrame(({ gl }) => {
    const session = gl.xr.getSession();
    if (session === null) {
      down.current = null;
      return;
    }
    const now = pressedButtons(session.inputSources);
    const before = down.current;
    // Recorded before firing: an intent that throws must not fire again on every frame.
    down.current = now;
    if (before === null) return;
    for (const intent of newPresses(before, now)) {
      try {
        fireIntent(intent);
      } catch (error) {
        console.error(`input: controller intent ${intent} failed`, error);
      }
    }
  });
  return null;
}
