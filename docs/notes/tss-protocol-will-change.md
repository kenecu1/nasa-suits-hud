NASA says the current TSS is not final, and its FY27 FAQ says the TSS sends all data as JSON/GeoJSON over WebSocket; expect the wire format to change completely.

- TSS2027 README, first line: not the final version, everything subject to change.
- FY27 FAQ: TSS is "mostly JavaScript/TypeScript", data over WebSocket as JSON/GeoJSON. The repo today is a C server speaking UDP. One of them will give way.
- NASA plans to release telemetry to selected teams mid-December 2026 to early January 2027.
- Already unstable: XRF and CTS layouts ("still to define" in code), where suit telemetry and position live, payload sizes, DCU flag meanings, procedures and coordinates (the documents in the repo are from 2025-26).

**Rule:** only `backend/suits/tss/` knows TSS wire formats, ports and field names. It outputs our own `TssSnapshot` model. Nothing else imports from it except that model. A protocol change means a new or edited adapter plus new fixtures, and no change elsewhere.

Before each milestone that touches the adapter, run `git log -5` in the TSS clone after `git pull` and compare with the commit recorded in `backend/suits/tss/VERSION`.
