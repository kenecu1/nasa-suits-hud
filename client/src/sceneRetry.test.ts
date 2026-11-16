import { expect, it } from "vitest";
import { retryDelayMs } from "./sceneRetry";

it.each([
  [1, 2000],
  [2, 4000],
  [3, 8000],
  [4, 16_000],
  [5, 30_000],
  [50, 30_000],
])("failure %i in a row waits %i ms before the scene is rebuilt", (failures, ms) => {
  expect(retryDelayMs(failures)).toBe(ms);
});

it("never waits less than the first delay", () => {
  expect(retryDelayMs(0)).toBe(2000);
  expect(retryDelayMs(-3)).toBe(2000);
});
