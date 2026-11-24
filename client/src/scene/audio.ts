// Web Audio for the warning tone. Browsers keep audio locked until the page has had a click or
// key press, so main.tsx calls `unlockAudio` on the first one. A beep while locked is not
// queued (it would sound late, after the fact): it is reported as blocked instead.
import { theme } from "../theme";

let audio: AudioContext | null = null;

function context(): AudioContext {
  audio ??= new AudioContext();
  return audio;
}

export function unlockAudio(): void {
  try {
    const ctx = context();
    if (ctx.state !== "running") ctx.resume().catch((error: unknown) => console.warn("tone: audio could not start", error));
  } catch (error) {
    console.warn("tone: no audio on this page", error);
  }
}

export type BeepResult = "played" | "blocked";

export function beep(): BeepResult {
  const ctx = context();
  if (ctx.state !== "running") {
    console.warn(`tone: warning tone not played (audio is ${ctx.state}; it starts after the first key press or click)`);
    return "blocked";
  }
  const { frequencyHz, durationS, gain } = theme.tone;
  const osc = ctx.createOscillator();
  const level = ctx.createGain();
  osc.frequency.value = frequencyHz;
  level.gain.setValueAtTime(gain, ctx.currentTime);
  level.gain.exponentialRampToValueAtTime(theme.tone.floorGain, ctx.currentTime + durationS);
  osc.connect(level).connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + durationS);
  return "played";
}
