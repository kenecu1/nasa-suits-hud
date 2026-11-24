In NASA's simulation only the active fan spins: the inactive one reads 0 rpm, which ranges.json classes as warning, so per-value levels alone cannot tell "broken" from "switched off".

From `update_fan_values` in `vendor/TSS2027/src/data.c` (commit 7dfc42b): with `dcu.fan` on primary, `fan_pri_rpm` is 30000 and `fan_sec_rpm` 0; on secondary the reverse. Scrubbers are similar: the active one fills, the inactive one vents (`update_scrubber_state_EVA`).

- Alerts handle it: the fan and CO2 rules in `data/alerts.json` watch only the device the DCU switch selects (`switch` + `by_position`), so the inactive fan raises nothing (M2, decision D).
- `State.suit.values.fan_sec_rpm.level` is still `warning` while the primary runs. A panel that draws every value (details page, vitals) shows it in warning style unless the backend marks the device inactive. Decide that in the backend or contract, not in a view model.
- Our fake (`backend/suits/sim/dynamics.py`) copies this rule, so sim mode shows the same thing as the real TSS.
