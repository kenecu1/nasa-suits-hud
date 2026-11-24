import { afterEach, describe, expect, it, vi } from "vitest";
import type { Command } from "../contract.gen";
import { buildHud } from "../hud/hud";
import type { HudPanels } from "../hud/types";
import { newPresses, pressedButtons, type InputSourceLike } from "./buttonPresses";
import { createIntentHandler, fireIntent, setIntentHandler } from "./dispatch";
import { commandFor, INTENTS, KEYBOARD, XR_BUTTONS, type Intent } from "./intents";
import { intentForKey, startKeyboard, type KeyLike } from "./keyboard";

function panelsWithTop(id: string | null): HudPanels {
  const panels = buildHud(null, "connecting");
  return { ...panels, banner: { ...panels.banner, topId: id } };
}

describe("binding tables", () => {
  it("bind every intent once on the keyboard and once on the controller", () => {
    for (const intent of INTENTS) {
      expect(Object.values(KEYBOARD).filter((i) => i === intent)).toHaveLength(1);
      expect(XR_BUTTONS.filter((b) => b.intent === intent)).toHaveLength(1);
    }
  });

  it("puts ack_alert on key A and on the controller's A button", () => {
    expect(KEYBOARD.KeyA).toBe("ack_alert");
    expect(XR_BUTTONS.find((b) => b.intent === "ack_alert")).toMatchObject({ handedness: "right", button: "a-button", index: 4 });
  });

  it("puts toggle_details on key D and the B button", () => {
    expect(KEYBOARD.KeyD).toBe("toggle_details");
    expect(XR_BUTTONS.find((b) => b.intent === "toggle_details")).toMatchObject({ button: "b-button", index: 5 });
  });
});

describe("commandFor", () => {
  it("acknowledges the id the banner shows on top (decision B)", () => {
    expect(commandFor("ack_alert", panelsWithTop("fan"))).toEqual({ type: "command", name: "ack_alert", args: { id: "fan" } });
  });

  it("sends no id when nothing is on top, so the backend acks its own top", () => {
    expect(commandFor("ack_alert", panelsWithTop(null)).args.id).toBeNull();
  });

  it("toggles the details page without an id", () => {
    expect(commandFor("toggle_details", panelsWithTop("fan"))).toEqual({
      type: "command",
      name: "toggle_details",
      args: { id: null },
    });
  });
});

describe("keyboard", () => {
  const key = (code: string, extra: Partial<KeyLike> = {}): KeyLike => ({
    code,
    repeat: false,
    ctrlKey: false,
    altKey: false,
    metaKey: false,
    target: null,
    ...extra,
  });

  it.each<[string, Intent]>([
    ["KeyA", "ack_alert"],
    ["KeyD", "toggle_details"],
  ])("maps %s to %s", (code, intent) => {
    expect(intentForKey(key(code))).toBe(intent);
  });

  it.each<[string, KeyLike]>([
    ["an unbound key", key("KeyQ")],
    ["a held key", key("KeyA", { repeat: true })],
    ["a shortcut", key("KeyA", { ctrlKey: true })],
    ["alt", key("KeyA", { altKey: true })],
    ["meta", key("KeyA", { metaKey: true })],
    ["typing in a field", key("KeyA", { target: { tagName: "INPUT" } })],
    ["typing in editable text", key("KeyA", { target: { isContentEditable: true } })],
    ["an inherited property name", key("toString")],
  ])("ignores %s", (_name, event) => {
    expect(intentForKey(event)).toBeNull();
  });

  it("listens for keydown and stops listening when told", () => {
    const listeners = new Map<string, (e: KeyboardEvent) => void>();
    const target = {
      addEventListener: (type: string, fn: (e: KeyboardEvent) => void) => listeners.set(type, fn),
      removeEventListener: (type: string) => listeners.delete(type),
    } as unknown as Window;
    const fired: Intent[] = [];
    const stop = startKeyboard((i) => fired.push(i), target);
    listeners.get("keydown")?.(key("KeyA") as unknown as KeyboardEvent);
    expect(fired).toEqual(["ack_alert"]);
    stop();
    expect(listeners.has("keydown")).toBe(false);
  });
});

describe("controller buttons", () => {
  const source = (handedness: string, pressed: number[]): InputSourceLike => ({
    handedness,
    gamepad: { buttons: Array.from({ length: 7 }, (_, i) => ({ pressed: pressed.includes(i) })) },
  });

  it("finds the bound buttons that are down", () => {
    expect(pressedButtons([source("right", [4])])).toEqual(new Set(["right:4"]));
    expect(pressedButtons([source("right", [0, 1, 3])])).toEqual(new Set());
  });

  it("ignores the left hand, a missing gamepad and missing buttons", () => {
    expect(pressedButtons([source("left", [4, 5])])).toEqual(new Set());
    expect(pressedButtons([{ handedness: "right", gamepad: null }, { handedness: "right" }])).toEqual(new Set());
    expect(pressedButtons([{ handedness: "right", gamepad: { buttons: [null, undefined] } }])).toEqual(new Set());
  });

  it("fires once when a button goes down, not while it is held, and again after release", () => {
    const up = pressedButtons([source("right", [])]);
    const a = pressedButtons([source("right", [4])]);
    expect(newPresses(up, a)).toEqual(["ack_alert"]);
    expect(newPresses(a, a)).toEqual([]);
    expect(newPresses(a, up)).toEqual([]);
    expect(newPresses(up, a)).toEqual(["ack_alert"]);
  });

  it("fires both when A and B go down in the same frame", () => {
    expect(newPresses(new Set(), pressedButtons([source("right", [4, 5])]))).toEqual(["ack_alert", "toggle_details"]);
  });
});

describe("dispatch", () => {
  afterEach(() => setIntentHandler(null));

  it("turns an intent into a command, sends it and records the outcome", () => {
    const sent: Command[] = [];
    const records: unknown[] = [];
    const handle = createIntentHandler({
      send: (c) => {
        sent.push(c);
        return true;
      },
      panels: () => panelsWithTop("oxygen"),
      onRecord: (r) => records.push(r),
    });
    const record = handle("ack_alert");
    expect(sent).toEqual([{ type: "command", name: "ack_alert", args: { id: "oxygen" } }]);
    expect(record).toEqual({ intent: "ack_alert", command: sent[0], sent: true });
    expect(records).toEqual([record]);
  });

  it("records a dropped command as not sent", () => {
    const handle = createIntentHandler({ send: () => false, panels: () => panelsWithTop(null) });
    expect(handle("toggle_details")?.sent).toBe(false);
  });

  it("reads the banner at the moment of the press, not when the handler was made", () => {
    let top: string | null = "fan";
    const sent: Command[] = [];
    const handle = createIntentHandler({ send: (c) => sent.push(c) > 0, panels: () => panelsWithTop(top) });
    top = "oxygen";
    handle("ack_alert");
    expect(sent[0]?.args.id).toBe("oxygen");
  });

  it("says so in the console when an intent fires with no handler", () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(fireIntent("ack_alert")).toBeNull();
    expect(error).toHaveBeenCalledWith(expect.stringContaining("ack_alert has nowhere to go"));
    error.mockRestore();
  });

  it("passes a fired intent to the handler that is set", () => {
    const seen: Intent[] = [];
    setIntentHandler((intent) => {
      seen.push(intent);
      return null;
    });
    fireIntent("toggle_details");
    expect(seen).toEqual(["toggle_details"]);
  });
});
