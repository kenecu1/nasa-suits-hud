// Intent → command → backend. One handler for the page, set by main.tsx once the link exists;
// the keyboard and the controller buttons both call `fireIntent`. The client never changes
// what it shows here: the backend's next State does (brief section 6, "After acknowledge").
import type { Command } from "../contract.gen";
import type { HudPanels } from "../hud/types";
import { commandFor, type Intent } from "./intents";

export interface IntentRecord {
  intent: Intent;
  command: Command;
  /** False when the link dropped it (not connected). There is no queue. */
  sent: boolean;
}

export type IntentHandler = (intent: Intent) => IntentRecord | null;

let handler: IntentHandler | null = null;

export function createIntentHandler(options: {
  send: (command: Command) => boolean;
  panels: () => HudPanels;
  onRecord?: (record: IntentRecord) => void;
}): IntentHandler {
  return (intent) => {
    const command = commandFor(intent, options.panels());
    const sent = options.send(command);
    const record = { intent, command, sent };
    options.onRecord?.(record);
    return record;
  };
}

export function setIntentHandler(next: IntentHandler | null): void {
  handler = next;
}

export function fireIntent(intent: Intent): IntentRecord | null {
  if (handler === null) {
    console.error(`input: intent ${intent} has nowhere to go (no handler set)`);
    return null;
  }
  return handler(intent);
}
