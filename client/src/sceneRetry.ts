// How long to wait before building a crashed scene again. It doubles after each failure in a
// row, so data that keeps breaking the scene does not rebuild it every two seconds for ever.
const FIRST_MS = 2000;
const MAX_MS = 30_000;

/** A rebuilt scene that runs this long without crashing starts the count from 1 again. */
export const FAILURES_RESET_AFTER_MS = 60_000;

/** Wait before retry number `failures` (1 = first): 2, 4, 8, 16, then 30 s. */
export function retryDelayMs(failures: number): number {
  return Math.min(MAX_MS, FIRST_MS * 2 ** Math.max(0, failures - 1));
}
