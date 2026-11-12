# M7 — Science tasks at points of interest

**Goal:** at each point of interest the HUD shows the right task checklist, live data from the science devices, and logs samples on the map. NASA requirement 3a (station procedures), the spectrometer display, and "payload data at any time".

**Builder:** Sonnet 5.5. This milestone copies patterns from M2–M4; if something needs a new pattern, stop and ask. **Fable review:** no.

**Read first:** `docs/walkthroughs/M3.md` and `M4.md`; mission description page 6; notes `tss-readme-payload-sizes-wrong`, `tss-suit-telemetry-is-legacy-only`.

## Scope

1. **Station procedures** (`data/procedures/`): camera deployment, geology sampling (with a spectrometer reading), sample marker placement, science payload (the seismometer unit, SSU, or the solar power module, SPM), camera teardown. Mostly manual steps the wearer confirms; use `done_when` where the TSS has data (drill deployed, drill depth at target, SPM status complete). Each point of interest in `site.json` lists its procedures; arriving there offers them.
2. **Adapter:** legacy command 8 (spectrometer; the fake TSS serves rocks from a copy of `vendor/TSS2027/data/RockData.json` kept in `data/mission/`); decoding of SSU and SPM packets; the single science-device subscription follows the active procedure (the core asks for a device, the adapter switches).
3. **Science** (`core/science.py`, `science` in the contract): the current rock (name, id, oxide percentages); flags from `data/mission/xrf_rules.json` (our own placeholder rules, marked as such); a log of samples, each with time, position and composition, also added as a pin of type `sample`.
4. **Panels:** spectrometer panel (rock name, oxide bars, flag); payload panel (SSU: drill depth against target, temperature and thermal state; SPM: status, truss height, azimuth, voltage; no tilt, because the TSS always sends 0); a camera row that says "no data from TSS"; sample pins on the map.
5. **Scenarios:** `poi_geology`, `poi_payload`.

**Cut line:** payload panel and SSU/SPM decoding; keep the spectrometer and the checklists.

## Acceptance

Backend (pytest)
1. SSU: the captured idle packet in `tss-packet-format` decodes to power off, both drill temperatures −25.0, depths 0. SPM: a 28-byte zero payload decodes to all-off values; a 27-byte payload is rejected.
2. Starting a payload procedure makes the adapter subscribe to that device (seen by the fake TSS); starting another switches it.
3. Scenario `poi_geology`: setting a rock id shows the rock in `science.xrf`, a rule flag when a rule matches, one log entry and one `sample` pin at the current position. Scanning the same rock twice does not log twice.
4. Scenario `poi_payload`: `done_when` steps complete as the drill reaches target depth.
5. All new procedure files pass the M3 schema test.

Client and end to end
6. View models for the spectrometer and payload panels, including "no rock scanned" and "no data".
7. Playwright: play `poi_geology`; screenshot with the spectrometer panel and the sample pin. Emulated headset view-model check.
8. Only if M6 is merged (otherwise M8 covers it): `get_science` is registered and "what rock is this" answers with the rock name.
