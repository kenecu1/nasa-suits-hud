// Every user action is an intent (CLAUDE.md). A device is only a binding table from its own
// keys or buttons to intents; everything after the table is shared. Voice (M6) will be one more
// source of the same intents. Later milestones add a row to each table for every new intent.
import type { Command } from "../contract.gen";
import type { HudPanels } from "../hud/types";

export type Intent = Command["name"];

/** Every intent, once. A Record, so adding a command name to the contract fails to compile here. */
const ALL: Record<Intent, true> = { ack_alert: true, toggle_details: true };
export const INTENTS = Object.keys(ALL) as Intent[];

/** Laptop keyboard, by `KeyboardEvent.code` (the key's place, whatever the layout prints on it). */
export const KEYBOARD: Readonly<Record<string, Intent>> = {
  KeyA: "ack_alert",
  KeyD: "toggle_details",
};

export interface XrButtonBinding {
  handedness: "left" | "right";
  /** The button's name in the WebXR input profile (Meta Quest Touch). */
  button: string;
  /** Its index in `gamepad.buttons` under the xr-standard mapping. */
  index: number;
  intent: Intent;
}

/** Headset controller buttons. On the right Quest controller, A is button 4 and B is button 5. */
export const XR_BUTTONS: readonly XrButtonBinding[] = [
  { handedness: "right", button: "a-button", index: 4, intent: "ack_alert" },
  { handedness: "right", button: "b-button", index: 5, intent: "toggle_details" },
];

/**
 * The command an intent becomes. `ack_alert` names the alert the banner shows on top
 * (decision B in docs/briefs/M2.md): a warning that arrived since the wearer looked is never
 * acknowledged by mistake. With nothing on top it sends no id, and the backend acks its own top.
 */
export function commandFor(intent: Intent, panels: HudPanels): Command {
  switch (intent) {
    case "ack_alert":
      return { type: "command", name: "ack_alert", args: { id: panels.banner.topId } };
    case "toggle_details":
      return { type: "command", name: "toggle_details", args: { id: null } };
    default: {
      // A new command name in the contract must get its own case, never fall into another.
      const unhandled: never = intent;
      throw new Error(`no command for intent ${String(unhandled)}`);
    }
  }
}
