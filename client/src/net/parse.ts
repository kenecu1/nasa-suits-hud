// Turn one WebSocket message into a State, or say why not. Never throws.
// The check is shallow on purpose: enough to know this is a contract v2 state. The view models
// treat any missing value inside it as unknown.
import type { State } from "../contract.gen";

// Typed from the generated contract: when the contract's version changes, this stops compiling.
export const CONTRACT_VERSION: State["v"] = 2;

export type ParseResult = { state: State } | { error: string };

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseState(raw: unknown): ParseResult {
  if (typeof raw !== "string") return { error: "not a text message" };

  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return { error: "not JSON" };
  }
  if (!isObject(data)) return { error: "not a JSON object" };
  if (data.type !== "state") return { error: `unexpected message type ${JSON.stringify(data.type)}` };
  if (data.v !== CONTRACT_VERSION) {
    return { error: `contract version ${JSON.stringify(data.v)}, this client reads version ${CONTRACT_VERSION}` };
  }
  if (!isObject(data.link) || typeof data.link.tss !== "string" || typeof data.link.mode !== "string") {
    return { error: "state without a usable link section" };
  }
  if (!isObject(data.suit) || !isObject(data.suit.values)) {
    return { error: "state without suit values" };
  }
  return { state: data as unknown as State };
}
