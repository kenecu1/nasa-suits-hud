// The warning tone: a short beep from Web Audio when the tone view model says so. Draws nothing.
import { useEffect, useRef } from "react";
import { useHud } from "../store";
import { theme } from "../theme";

let audio: AudioContext | null = null;

function beep(): void {
  audio ??= new AudioContext();
  const ctx = audio;
  // Browsers keep audio suspended until the page has had a click or key press; the first
  // warning after that plays. A suspended context is not an error worth more than a line.
  if (ctx.state === "suspended") {
    ctx.resume().catch((error: unknown) => console.warn("tone: audio could not start", error));
  }
  const { frequencyHz, durationS, gain } = theme.tone;
  const osc = ctx.createOscillator();
  const level = ctx.createGain();
  osc.frequency.value = frequencyHz;
  level.gain.setValueAtTime(gain, ctx.currentTime);
  level.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + durationS);
  osc.connect(level).connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + durationS);
}

export function Tone() {
  const tone = useHud((s) => s.panels.tone);
  const played = useRef<string | null>(null);
  useEffect(() => {
    // Once per state: a rebuild for the same state (the link going live) does not replay it.
    if (!tone.play || played.current === tone.key) return;
    played.current = tone.key;
    if (window.__hud) window.__hud.tones += 1;
    try {
      beep();
    } catch (error) {
      console.warn("tone: could not play the warning tone", error);
    }
  }, [tone]);
  return null;
}
