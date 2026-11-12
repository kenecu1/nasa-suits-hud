Suit telemetry, EVA status, fault flags, position and spectrometer data exist only on the old per-team UDP ports; the new subscription protocol carries only DCU, UIA, SPM and SSU.

Verified live against TSS2027 commit 6293795 (2026-11-10).

**Old path (still works):** UDP port `14142 + team` (teams 0–9). Request is 8 bytes big-endian: `uint32 timestamp, uint32 command`. The reply is JSON text for one section.

| Command | Section | Notes |
|---|---|---|
| 1 | telemetry | 23 values: 22 with ranges plus `eva_elapsed_time` |
| 2 | status | `started` |
| 3 | dcu | also in new protocol |
| 4 | error | `fan_error, oxy_error, power_error, scrubber_error` |
| 5 | imu | `posx, posy, heading` |
| 6 | uia | also in new protocol |
| 7 | ssu | also in new protocol |
| 8 | spec | scanned rock: id, name, oxide percentages |

**Command 0 (whole EVA.json) was removed** on 2026-10-19 (commit 21c2ff0). Our old `bridge/tss_client.py` sends 8 zero bytes, so it gets nothing.

Do not send old-style requests to port 14141: no reply, and commands 1–6 there register a bogus peripheral.

**New path:** see [tss-packet-format](tss-packet-format.md). XRF (6) and CTS (5) can be subscribed to (Ack 0) but nothing is ever sent.

**Consequence:** today the adapter needs both paths. Expect NASA to move suit telemetry into the new path; see [tss-protocol-will-change](tss-protocol-will-change.md).
