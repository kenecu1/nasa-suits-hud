// The warning tone: a short beep for every new warning the store has counted. Draws nothing.
// The store decides when (hud/tone.vm.ts, counted in store.ts), so a tone is neither lost when
// two states arrive before React draws nor repeated when this component mounts again.
import { useEffect } from "react";
import { useHud } from "../store";
import { beep } from "./audio";

/** Module-level, not a ref: it must survive this component being rebuilt after a HUD crash. */
let sounded = 0;

export function Tone() {
  const due = useHud((s) => s.toneCount);
  useEffect(() => {
    if (due <= sounded) return;
    sounded = due;
    let result: "played" | "blocked" | "failed";
    try {
      result = beep();
    } catch (error) {
      console.warn("tone: could not play the warning tone", error);
      result = "failed";
    }
    if (window.__hud) {
      if (result === "played") window.__hud.tones += 1;
      else window.__hud.tonesMissed += 1;
    }
  }, [due]);
  return null;
}
