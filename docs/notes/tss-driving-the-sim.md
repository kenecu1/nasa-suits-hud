The TSS simulation can be driven from a script: an HTTP form POST starts or resets the EVA and toggles faults, and legacy UDP commands 2001–2020 on the per-team ports set switches, position and the scanned rock.

Verified at commit 6293795 (`src/data.h` lines 114–144, `src/server.c`, `frontend/index.js`).

**HTTP (port 14141)**
- `POST /` with a form body `team=<digit>&<path>=<value>`, for example `team=0&eva.status.started=true`. Success returns 304, failure 400.
- Faults: `eva.error.fan_error`, `eva.error.oxy_error`, `eva.error.power_error`, `eva.error.scrubber_error` (true or false).
- Read back everything: `GET /data/instances/<team>/EVA.json` (the web page polls this every second).
- Group and team assignment: `POST /groups` (see [tss-team-must-be-assigned](tss-team-must-be-assigned.md)).

**Legacy UDP on port `14142 + team`:** 12 bytes big-endian `uint32 timestamp, uint32 command, float32 value` (1.0 or 0.0 for switches). Reply is 4 bytes `01 00 00 00`.

| Command | Sets |
|---|---|
| 2001–2004 | `uia.eva1_power`, `eva1_oxy`, `eva1_water_supply`, `eva1_water_waste` |
| 2005–2008 | the same four for `eva2` (not ours) |
| 2009, 2010 | `uia.oxy_vent`, `uia.depress` |
| 2011 | `dcu.batt.lu` |
| 2012 | `dcu.oxy` |
| 2013 | `dcu.batt.ps` |
| 2014 | `dcu.fan` |
| 2015 | `dcu.pump` |
| 2016 | `dcu.co2` |
| 2017, 2018, 2019 | `imu.posx`, `imu.posy`, `imu.heading` |
| 2020 | `spec.id` (rock id; data comes from `data/RockData.json`) |

- There is no UDP command for `dcu.comm`.
- These commands are dropped on port 14141. `scripts/simulate_position.py` in the TSS repo sends there and also reuses 2020–2022 for a second crew member; do not copy it.
- After the EVA starts, most suit values are live at once (battery near 100, tanks near 3000 psi). `coolant_storage` and `suit_pressure_oxy` stay at 0 until the egress steps fill and pressurise them.
- The TSS does not define the heading convention. We define it: degrees, 0 = map north (+Y), clockwise. The adapter is the place to convert if NASA defines another.
- Faults are not flags in the new protocol; they show in legacy GET 4 and through their effect on values.

Use: our scenario driver (plays a whole mission for end-to-end tests, ML training data and demos).
