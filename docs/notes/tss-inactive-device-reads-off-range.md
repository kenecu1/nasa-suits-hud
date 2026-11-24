In NASA's simulation only the active fan spins: the inactive one reads 0 rpm, which ranges.json classes as warning, so per-value levels alone cannot tell "broken" from "switched off".

From `update_fan_values` in `vendor/TSS2027/src/data.c` (commit 7dfc42b): with `dcu.fan` on primary, `fan_pri_rpm` is 30000 and `fan_sec_rpm` 0; on secondary the reverse. Scrubbers are similar: the active one fills, the inactive one vents (`update_scrubber_state_EVA`).

- Alerts handle it: the fan and CO2 rules in `data/alerts.json` watch only the device the DCU switch selects (`switch` + `by_position`), so the inactive fan raises nothing (M2, decision D).
- Values: since M2 session 2 the backend gives the fan the DCU switch does not select the level `off` (`active_when` in `data/ranges.json`, read by `core/store.py`), and the HUD draws it dimmed with a dash and the word OFF. Only the fans: the inactive scrubber still gets its normal level. With the DCU position unknown or stale, neither fan is `off`.
- Our fake (`backend/suits/sim/dynamics.py`) copies this rule, so sim mode shows the same thing as the real TSS.
