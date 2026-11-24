// The only place that listens to headset controller buttons. Once a frame it reads the
// session's raw WebXR gamepads (no controller model or profile download needed, so tests stay
// offline) and fires the intent of every bound button that has just gone down.
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import { fireIntent } from "./dispatch";
import { newPresses, pressedButtons } from "./buttonPresses";

const NONE: ReadonlySet<string> = new Set();

export function XrButtons() {
  const down = useRef<ReadonlySet<string>>(NONE);
  useFrame(({ gl }) => {
    const session = gl.xr.getSession();
    if (session === null) {
      down.current = NONE;
      return;
    }
    const now = pressedButtons(session.inputSources);
    for (const intent of newPresses(down.current, now)) fireIntent(intent);
    down.current = now;
  });
  return null;
}
