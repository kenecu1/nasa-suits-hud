# M5 — Forecast and predicted range

**Goal:** the HUD shows how long each consumable will last, how far the astronaut can still go, and tells them when to turn back. The forecast is a trained model with an honest evaluation against a simple baseline. NASA requirement 4d.

**Builder:** Opus 5.5. **Fable review after:** yes, of the evaluation method (data splits, leakage, whether the claims in the report follow from the numbers).

**Read first:** `docs/walkthroughs/M2.md`; the TSS simulation code in `vendor/TSS2027/src/` (`lib/simulation/` and the telemetry update functions in `data.c`) — read it in a Sonnet subagent and keep a summary.

## Scope

1. **Simulator** (`sim/dynamics.py`): port the TSS's telemetry update rules to Python and plug them into the fake TSS. Parameters: consumption rates, workload profile, sensor noise, faults (fan, oxygen, power, scrubber) with start times. It can run much faster than real time.
2. **Check against the real TSS:** a test replays a real recording's inputs through the simulator and compares the outputs. Use `backend/tests/fixtures/legacy-sample.jsonl` (6 minutes, no egress) now. Ask the user for a longer recording that includes an egress (`npm run tss:smoke -- --record`); when it exists, add it to the same test.
3. **Dataset** (`ml/train.py`): 500 simulated EVAs with randomised parameters and faults, saved as Parquet in `data/ml/` (gitignored; a fixed seed makes it reproducible). Split by run, never by time step: train, validation, test. Real recordings are an extra test set that is never trained on.
4. **Targets:** seconds until each consumable reaches its limit from `data/ranges.json`: primary oxygen storage, primary battery, scrubber CO2 storage, coolant storage.
5. **Baseline:** straight-line extrapolation of the last 60 s.
6. **Model:** gradient-boosted trees (scikit-learn) on window features (current value, slopes over 30, 60 and 300 s, workload indicators, fault flags), with quantile outputs for a low and high bound.
7. **Evaluation** (`ml/evaluate.py` → `docs/ml/forecast-report.md`): error by time-to-limit bucket, coverage of the low–high interval, model against baseline, separately for nominal runs, fault runs and real recordings. State the limits plainly: the data is simulated and the TSS's dynamics are simple.
8. **Ship the winner:** the backend loads whichever of baseline and model the report shows is better on the test set. If the baseline wins, say so in the report.
9. **Range and turn-back** (`ml/forecast.py`, `forecast` in the contract):
   - `time_left_s` = the smallest consumable time, using the low bound.
   - `max_range_m` = walking speed × (`time_left_s` − reserve) / 2 (out and back), with speed from M4 or the default.
   - `return_margin_s` = `time_left_s` − reserve − time to walk the return route (straight-line distance to the lander until M4 is merged).
   - A caution when the margin falls below 5 minutes, a warning "turn back now" below 0. Reserve is in config.
10. **Panels:** time left on each consumable bar; a range line on the consumables panel; a range ring on the map once M4 is merged.

## Acceptance

Backend (pytest)
1. Simulator: with fixed parameters and no noise the output matches a golden trajectory. With `legacy-sample.jsonl` (and any newer real recording present), each consumable stays within 5% of the recorded value over the recording.
2. Dataset: no run id appears in more than one split. Generation with the same seed gives the same data (compare a hash of the sorted values, not of the file).
3. Features use only samples at or before the prediction time (a test shifts future values and checks features do not change).
4. Baseline on an exactly linear series predicts time to limit within 1%.
5. `npm run ml:train` then `npm run ml:evaluate` (both added in this milestone) finish in under 10 minutes on a laptop CPU and write the report with every section present.
6. The shipped predictor is the one the report marks as the winner (the test reads the report's result file).
7. Range maths: table tests for `max_range_m` and `return_margin_s`. Scenario `long_traverse`: the caution, then the "turn back now" warning, appear at the expected margins.
8. Inference for one snapshot takes under 20 ms.

Client and end to end
9. View models show time left as `h:mm` and "—" when unknown. Screenshot with the forecast visible. Emulated headset view-model check.

## For the review

Hand the reviewer `docs/ml/forecast-report.md`, `ml/train.py`, `ml/features.py`, `ml/evaluate.py` and this file.
