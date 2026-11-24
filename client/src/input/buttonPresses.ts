// Controller buttons to intents, as plain logic (input/XrButtons.tsx polls the session once a
// frame and calls this). A button fires once when it goes down, not again while it is held.
import { XR_BUTTONS, type Intent } from "./intents";

export interface InputSourceLike {
  handedness: string;
  gamepad?: { buttons: readonly ({ pressed: boolean } | null | undefined)[] } | null;
}

/** "right:4" for every bound button that is down now. */
export function pressedButtons(sources: Iterable<InputSourceLike>): Set<string> {
  const down = new Set<string>();
  for (const source of sources) {
    for (const binding of XR_BUTTONS) {
      if (source.handedness !== binding.handedness) continue;
      if (source.gamepad?.buttons[binding.index]?.pressed === true) down.add(`${binding.handedness}:${binding.index}`);
    }
  }
  return down;
}

/** The intents of buttons that are down now and were not down before, in table order. */
export function newPresses(before: ReadonlySet<string>, now: ReadonlySet<string>): Intent[] {
  return XR_BUTTONS.filter((b) => {
    const key = `${b.handedness}:${b.index}`;
    return now.has(key) && !before.has(key);
  }).map((b) => b.intent);
}
