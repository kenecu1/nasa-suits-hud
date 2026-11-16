import { describe, expect, it } from "vitest";
import { wsUrl } from "./backendUrl";

describe("wsUrl", () => {
  it.each([
    ["http://localhost:5173/", "ws://localhost:5173/ws"],
    ["http://localhost:5173/some/path?emulator=off#x", "ws://localhost:5173/ws"],
    ["https://hud.example.test/", "wss://hud.example.test/ws"],
    ["http://192.168.1.20:5173/", "ws://192.168.1.20:5173/ws"],
  ])("turns %s into %s", (pageUrl, expected) => {
    expect(wsUrl(pageUrl)).toBe(expected);
  });
});
