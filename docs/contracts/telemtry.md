# Telemetry Message Contract (Bridge to HUD)

**Ticket:** SUITS-20
**Version:** 1

## 1. Purpose

This document defines every message the bridge sends to the HUD over WebSocket. Both tracks build against this contract, so the bridge (Python) and the HUD (React) can be developed at the same time without waiting on each other.

Data flow:

```
TSS (server) → UDP → Bridge (Python) → WebSocket → HUD (React)
```

The HUD never talks to the TSS directly. Every message the HUD receives comes from the bridge.

## 2. Message types

The bridge sends one of two message types, decided by whether the TSS answered its poll.

| State | Message type | How the HUD tells |
|---|---|---|
| TSS down or sending bad data | `tss_error` | The type itself, plus `reason` |
| TSS up, EVA not started | `telemetry` | `data.status.started` is `false` |
| TSS up, EVA running | `telemetry` | `data.status.started` is `true` |

"EVA not started" is not its own type. The TSS is answering; its answer just says the EVA has not begun. Many values read 0 in this state, which is expected and should not trigger alarms.

## 3. Envelope

Every message has these top level fields.

| Field | Type | Present in | Meaning |
|---|---|---|---|
| `type` | text | all | `"telemetry"` or `"tss_error"` |
| `version` | number (integer) | all | Contract version. Currently `1` |
| `timestamp` | number | all | When the bridge sent the message, Unix time in **seconds** (from Python `time.time()`) |
| `data` | object | `telemetry` only | TSS data, grouped (see section 4) |
| `reason` | text | `tss_error` only | `"unreachable"` or `"bad_data"` |
| `age` | number or `null` | `tss_error` only | Seconds since the last good telemetry. `null` if the bridge has never received good data |

**Error reasons:**
* `unreachable`: the TSS did not reply before the bridge timeout (Python `OSError`)
* `bad_data`: the TSS replied, but the reply could not be parsed or did not have the expected shape (Python `ValueError`, `TypeError`, `KeyError`)

## 4. Data fields (v1)

`data` contains three groups: `telemetry`, `status`, and `error`. All other TSS groups (`dcu`, `uia`, `imu`, `ssu`, `spec`) are out of scope for v1 and will be added in later versions.

### 4a. `data.telemetry`

| Field | Unit | Type | Notes |
|---|---|---|---|
| `primary_battery_level` | % | number | |
| `secondary_battery_level` | % | number | |
| `oxy_pri_storage` | % | number | Primary O2 tank level |
| `oxy_sec_storage` | % | number | Secondary O2 tank level |
| `oxy_pri_pressure` | psi | number | Primary O2 tank pressure |
| `oxy_sec_pressure` | psi | number | Secondary O2 tank pressure |
| `suit_pressure_oxy` | psi | number | O2 pressure inside suit, target 4.0 |
| `suit_pressure_co2` | psi | number | |
| `suit_pressure_other` | psi | number | |
| `suit_pressure_total` | psi | number | |
| `helmet_pressure_co2` | psi | number | |
| `fan_pri_rpm` | rpm | number | Nominal 30,000 |
| `fan_sec_rpm` | rpm | number | Nominal 30,000 |
| `scrubber_a_co2_storage` | % | number | |
| `scrubber_b_co2_storage` | % | number | |
| `temperature` | °C | number | Inside suit |
| `coolant_storage` | % | number | |
| `coolant_gas_pressure` | psi | number | |
| `coolant_liquid_pressure` | psi | number | Defaults to about 500 psi; not necessarily a live change |
| `heart_rate` | bpm | number | |
| `oxy_consumption` | psi/min | number | O2 usage rate |
| `co2_production` | psi/min | number | |
| `eva_elapsed_time` | seconds | number (integer) | Stays 0 until the EVA starts |

### 4b. `data.status`

| Field | Type | Meaning |
|---|---|---|
| `started` | true/false | Whether the EVA has started |

### 4c. `data.error`

Suit hardware fault flags. These are **not** connection errors (those use `tss_error`). All should normally be `false`.

| Field | Type | Meaning |
|---|---|---|
| `fan_error` | true/false | Fan fault |
| `oxy_error` | true/false | Oxygen fault |
| `power_error` | true/false | Power fault |
| `scrubber_error` | true/false | CO2 scrubber fault |

Normal ranges for caution and warning live in NASA's `documents/telemetry_ranges/eva-telemetry-ranges.pdf` and in `docs/tss-notes.md`. They are intentionally not part of this contract.

## 5. Example messages

### 5a. Telemetry (EVA running)

```json
{
  "type": "telemetry",
  "version": 1,
  "timestamp": 1761017452.318,
  "data": {
    "telemetry": {
      "primary_battery_level": 84.2134,
      "secondary_battery_level": 100.0,
      "oxy_pri_storage": 71.6524,
      "oxy_sec_storage": 100.0,
      "oxy_pri_pressure": 2148.9172,
      "oxy_sec_pressure": 2999.8811,
      "suit_pressure_oxy": 4.0012,
      "suit_pressure_co2": 0.0412,
      "suit_pressure_other": 0.0,
      "suit_pressure_total": 4.0424,
      "helmet_pressure_co2": 0.0618,
      "fan_pri_rpm": 30000,
      "fan_sec_rpm": 30000,
      "scrubber_a_co2_storage": 23.4571,
      "scrubber_b_co2_storage": 0.0,
      "temperature": 22.8133,
      "coolant_storage": 94.5102,
      "coolant_gas_pressure": 0.0,
      "coolant_liquid_pressure": 501.8415,
      "heart_rate": 92.3307,
      "oxy_consumption": 0.1036,
      "co2_production": 0.1121,
      "eva_elapsed_time": 1843
    },
    "status": {
      "started": true
    },
    "error": {
      "fan_error": false,
      "oxy_error": false,
      "power_error": false,
      "scrubber_error": false
    }
  }
}
```

### 5b. Error (TSS unreachable)

```json
{
  "type": "tss_error",
  "version": 1,
  "timestamp": 1761017464.902,
  "reason": "unreachable",
  "age": 12.6
}
```

### 5c. Error (bridge never received good data)

```json
{
  "type": "tss_error",
  "version": 1,
  "timestamp": 1761017001.115,
  "reason": "unreachable",
  "age": null
}
```

## 6. Timing and staleness

**Bridge side**
* The bridge polls the TSS about once per second (poll, then `sleep(1)`), so a normal cycle is slightly over 1 second.
* The bridge waits up to `timeout_seconds` (from `bridge/config.json`) for a TSS reply. A failed cycle therefore takes `timeout_seconds + 1` seconds.
* The bridge sends exactly one message per cycle: `telemetry` on success, `tss_error` on failure.

**HUD side**
1. On every message, the HUD records its own receive time.
2. If `type` is `tss_error`: keep showing the last values, mark them stale, and show a warning using `reason` and `age` (for example "TSS offline, last data 12s ago").
3. If `type` is `telemetry` and `data.status.started` is `false`: show "EVA not started" and suppress range alarms.
4. If `type` is `telemetry` and `data.status.started` is `true`: show live values.
5. If **no message of any kind** arrives for **3 seconds**, the bridge or WebSocket itself is down. The HUD keeps the last values, marks them stale, and shows "Bridge offline." (`tss_error` cannot cover this case, because a dead bridge cannot send anything.)
6. If `version` is not `1`, show "Contract version mismatch, update the HUD" instead of reading `data`.

## 7. Decisions

| Topic | Decision | Reason |
|---|---|---|
| Rounding | Bridge sends full precision; HUD rounds at display | Range prediction, the replay recorder (SUITS-23), and future ML need true values. Display is a UI concern |
| Timestamp units | Unix seconds | Matches Python `time.time()`. HUD multiplies by 1000 for a JavaScript `Date` |
| Field names | Identity mapping in the bridge | Names are ours and currently match the TSS. If NASA renames a field, only the bridge mapping changes and the HUD is unaffected |
| Nesting | TSS groups under `data` | Keeps envelope fields separate from TSS data. Error messages simply have no `data` |
| Versioning | Adding fields keeps the version. Renaming, removing, or moving fields bumps it | New groups are ignored by older HUD code; breaking changes must fail loudly |
| Error types | One `tss_error` type with `reason` | The HUD responds the same way to both failures; only the warning text differs. Mirrors the bridge's two `except` blocks |

## 8. Notes

* `timeout_seconds` in `bridge/config.json` should stay under 1 second.
* NASA notes the TSS 2027 is not final. After each `git pull` of TSS2027, check `documents/updates` for renamed fields.
* Normal ranges for caution and warning are in `documents/telemetry_ranges/eva-telemetry-ranges.pdf` and `docs/tss-notes.md`.
