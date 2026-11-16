For about 3 s after the backend starts in sim mode, `link.tss` is `unreachable`, then `stale`, then `ok`; a test that asserts on the link right after a start must wait for `ok` first.

Seen in M1 (2026-11-16): the first desktop Playwright test failed now and then with "TSS STALE".

- This is correct behaviour, not a bug: telemetry, status and faults arrive one request at a time (see [tss-legacy-port-is-slow](tss-legacy-port-is-slow.md)), and the link is `ok` only when all have arrived.
- `e2e/support/backend.ts` waits until `/health` reports `"tss": "ok"` before a test runs. Do the same in any new harness that starts the backend.
- The end-to-end tests start and stop the backend themselves, on ports 8011 (backend) and 5183 (client), so they can run while `npm run dev` is open.
