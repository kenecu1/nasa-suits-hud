The TSS README gives wrong payload sizes for UIA, SPM and SSU; trust `src/data.c` (`build_telemetry_payload`) and the layouts below.

Verified at commit 6293795. Payload = bytes after the 10-byte header, before the checksum. A flag is one byte, 0 or 1.

**DCU (device 1), 6 bytes:** 0 batt (1 = UMB, 0 = LOCAL), 1 oxy, 2 comm, 3 fan, 4 pump (1 = OPEN), 5 co2. For PRI/SEC meaning see [tss-dcu-switch-meaning](tss-dcu-switch-meaning.md).

**UIA (device 2), 12 bytes sent, only 6 valid:** 0 eva_power, 1 water_supply, 2 water_waste, 3 o2_supply, 4 o2_vent, 5 depress. Bytes 6–11 are uninitialised memory. Ignore them. (README says 6 bytes.)

**SPM (device 3), 28 bytes** (README says 11):

| Offset | Field | Type |
|---|---|---|
| 0 | power | flag |
| 1 | status | 0 off, 1 booting, 2 leveling, 3 deploying, 4 orienting, 5 complete |
| 2 | mode | 0 LEVEL, 1 ORIENT |
| 3 | level | flag |
| 4 | level_locked | flag |
| 5 | truss | 0 stowed, 1 unlocked, 2 raising, 3 deployed, 4 locked |
| 6 | azimuth_aligned | flag |
| 7 | orientation_locked | flag |
| 8 | tilt_x | f32 |
| 12 | tilt_y | f32 |
| 16 | truss_height | f32, 0–1 |
| 20 | azimuth | f32 |
| 24 | voltage | f32 |

SPM is the Solar Power Module. Its `tilt_x` and `tilt_y` are always 0 in the packet: the packet builder reads `spm.tilt.x` but the simulation writes `tilt_x` (`data.c:1451`, `spm_sim.c:295`). Do not show tilt.

**SSU (Seismometer Sensing Unit, device 4), 33 bytes** (README says 15): bytes 0–2 are power (flag), status (0 off, 1 booting, 2 ready), mode (0 SP, 1 BB). Then two 15-byte drill blocks, SP at 3 and BB at 18:

| +Offset | Field | Type |
|---|---|---|
| 0 | sensor | 0 stowed, 1 primed, 2 deployed (unknown string → 255) |
| 1 | state | 0 idle, 1 drilling, 2 overheated, 3 retracting, 4 retracted, 5 deployed |
| 2 | thermal | 0 nominal, 1 warning, 2 critical |
| 3 | depth | f32, cm |
| 7 | temp | f32, °C |
| 11 | rpm | f32 |

SSU rules (`src/lib/ssu_simulation/README.md`): target depth SP 50 cm, BB 80 cm; drill locks at 35 °C, unlocks at 25 °C; max 600 rpm.

The decoder must accept a payload that is longer than expected and must reject one that is shorter. These sizes are likely to change.
