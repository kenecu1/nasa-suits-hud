// The only place that listens to the laptop keyboard. Keys become intents through KEYBOARD.
import { KEYBOARD, type Intent } from "./intents";

export interface KeyLike {
  code: string;
  repeat: boolean;
  ctrlKey: boolean;
  altKey: boolean;
  metaKey: boolean;
  target: unknown;
}

/** The intent a key press means, or null: held keys, shortcuts and typing in a field mean nothing. */
export function intentForKey(event: KeyLike): Intent | null {
  if (event.repeat || event.ctrlKey || event.altKey || event.metaKey) return null;
  const target = event.target as { isContentEditable?: boolean; tagName?: string } | null;
  if (target?.isContentEditable === true || ["INPUT", "TEXTAREA", "SELECT"].includes(target?.tagName ?? "")) return null;
  return Object.hasOwn(KEYBOARD, event.code) ? (KEYBOARD[event.code] ?? null) : null;
}

export function startKeyboard(onIntent: (intent: Intent) => void, target: Pick<Window, "addEventListener" | "removeEventListener"> = window): () => void {
  const listener = (event: KeyboardEvent): void => {
    const intent = intentForKey(event);
    if (intent !== null) onIntent(intent);
  };
  target.addEventListener("keydown", listener);
  return () => target.removeEventListener("keydown", listener);
}
