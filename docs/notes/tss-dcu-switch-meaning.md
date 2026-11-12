DCU flags: 1 means primary (oxygen PRI, fan PRI, CO2 scrubber A, battery UMB, pump OPEN) and 0 means secondary; every switch starts at 0, and the battery primary/secondary switch is not in the DCU packet.

Confirmed from the simulation logic in `src/data.c` at commit 6293795 (the newer README table is the right one; the older table saying false = PRI is wrong).

| Flag | 1 | 0 (default) | Evidence |
|---|---|---|---|
| `batt.lu` (packet byte 0) | UMB | LOCAL | README, code |
| `oxy` (byte 1) | PRI | SEC | `o2 == true` uses the primary tank |
| `comm` (byte 2) | A | B | README only, not used by the simulation |
| `fan` (byte 3) | PRI | SEC | `fan == false` is the backup fan |
| `pump` (byte 4) | OPEN | CLOSED | README, code |
| `co2` (byte 5) | A | B | `co2 == true` fills scrubber A |

- `batt.ps` (primary or secondary battery) exists in the TSS state and has legacy command 2013, but it is not in the 6-byte DCU packet. It is readable through legacy GET 3 (dcu section).
- There is no legacy UDP command to set `comm`. It can only be set from the TSS web page.
- Because everything starts at 0, a fresh EVA is "on secondary" for oxygen, fan and CO2 until egress sets them.

**Rule:** the mapping from raw flag to a named position lives in one table in the TSS adapter. Everything after the adapter uses the named position, never the raw flag.
