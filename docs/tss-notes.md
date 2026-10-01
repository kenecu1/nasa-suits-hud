# TSS Notes: What the TSS Sends and How to Get It

Cheat sheet for reading data from NASA's Telemetry Stream Server (TSS2027).
For installing and starting the TSS, see [setup.md](setup.md).

---

## 1. Where to get the data

When you run `./server.exe`, it prints its address:
```
Launching Server at IP: 172.20.182.43:14141
```
Use **that IP** (yours will be different, and it can change after a restart).

### Teams
The TSS runs **10 separate fake suits**, called teams `0`–`9`. Each one has its own data. The TSS web page has a **team dropdown** at the top: make sure it matches the team your code reads. **We use team 0.**

### Option A: HTTP (easiest, works in a browser)
```
http://<IP>:14141/data/instances/<team>/EVA.json
```
Example for team 0: `http://172.20.182.43:14141/data/instances/0/EVA.json`

Open it in a browser and you see the full suit state as JSON. It's a snapshot: refresh (F5) to see new values. This is how NASA's own web page gets its data.

### Option B: UDP (the way NASA intends apps to connect)
| | |
|---|---|
| **Address** | the IP the server prints |
| **Port** | `14142 + team` → team 0 = **14142**, team 1 = 14143, … team 9 = 14151 |
| **How often** | once per second (the TSS only updates once per second, so faster is pointless) |

**Request:** 8 bytes, in big-endian byte order:
| Bytes 0–3 | Bytes 4–7 |
|---|---|
| UNIX timestamp (uint32) | command number (uint32) |

- Command **`0`** = "send me EVA.json".
- **Response:** the EVA.json text as raw bytes. Decode it as JSON.
- Commands 1000–2999 change values (e.g. flip a switch). Not needed for now.

NASA's working example: `scripts/test_socket.py` in the TSS2027 folder (about 15 lines of Python). It sends an all-zero 8-byte request to port 14151 once per second and prints the reply.

---

## 2. A real data message

Captured from team 0, about 80 seconds after starting the EVA:

```json
{
	"telemetry":	{
		"primary_battery_level":	96.0497589111328,
		"secondary_battery_level":	96.0497589111328,
		"oxy_pri_storage":	98.97296142578125,
		"oxy_sec_storage":	98.97296142578125,
		"oxy_pri_pressure":	2969.18896484375,
		"oxy_sec_pressure":	2969.18896484375,
		"suit_pressure_oxy":	0,
		"suit_pressure_co2":	0.078999981284141541,
		"suit_pressure_other":	0,
		"suit_pressure_total":	0.078999981284141541,
		"helmet_pressure_co2":	0.11849997192621231,
		"fan_pri_rpm":	30000,
		"fan_sec_rpm":	30000,
		"scrubber_a_co2_storage":	10.270007133483887,
		"scrubber_b_co2_storage":	10.270007133483887,
		"temperature":	26.129220962524414,
		"coolant_storage":	0,
		"coolant_gas_pressure":	0,
		"coolant_liquid_pressure":	501.84149169921875,
		"heart_rate":	160.50028991699219,
		"oxy_consumption":	0.11605002731084824,
		"co2_production":	0.14210005104541779,
		"eva_elapsed_time":	79
	},
	"status":	{
		"started":	true
	},
	"dcu":	{
		"oxy":	false,
		"fan":	false,
		"pump":	false,
		"co2":	false,
		"batt":	{
			"lu":	false,
			"ps":	false
		}
	},
	"error":	{
		"fan_error":	false,
		"oxy_error":	false,
		"power_error":	false,
		"scrubber_error":	false
	},
	"imu":	{
		"posx":	-5668.528809,
		"posy":	-10045.585938,
		"heading":	125.453674
	},
	"uia":	{
		"eva1_power":	false,
		"eva1_oxy":	false,
		"eva1_water_supply":	false,
		"eva1_water_waste":	false,
		"eva2_power":	false,
		"eva2_oxy":	false,
		"eva2_water_supply":	false,
		"eva2_water_waste":	false,
		"oxy_vent":	false,
		"depress":	false
	},
	"ssu":	{
		"power":	false,
		"status":	"off",
		"angle":	0,
		"mode":	0,
		"sp_depth":	0,
		"sp_sensor":	"not ready",
		"sp_target_depth":	50,
		"sp_temp":	-25,
		"sp_temp_warning":	15,
		"sp_temp_critical":	25,
		"sp_temp_unlock":	25,
		"sp_rpm":	0,
		"sp_state":	"idle",
		"sp_thermal":	"nominal",
		"mock_rpm":	0,
		"bb_deployed":	false
	},
	"spec":	{
		"eva1":	{
			"name":	"Default Rock",
			"type":	"default_rock",
			"id":	0,
			"data":	{
				"SiO2":	1,
				"TiO2":	1,
				"Al2O3":	1,
				"FeO":	1,
				"MnO":	1,
				"MgO":	1,
				"CaO":	1,
				"K2O":	1,
				"P2O3":	1,
				"other":	91
			}
		},
		"eva2":	{
			"name":	"Default Rock",
			"type":	"default_rock",
			"id":	0,
			"data":	{
				"SiO2":	1,
				"TiO2":	1,
				"Al2O3":	1,
				"FeO":	1,
				"MnO":	1,
				"MgO":	1,
				"CaO":	1,
				"K2O":	1,
				"P2O3":	1,
				"other":	91
			}
		}
	}
}
```

**How to read names:** dots mean "inside". `telemetry.oxy_pri_storage` = the `oxy_pri_storage` value inside the `telemetry` group.

---

## 3. Names of the important values

Units and normal ranges are from NASA's `documents/telemetry_ranges/eva-telemetry-ranges.pdf`. Values outside the normal range should trigger caution/warning alerts later.

### Oxygen
| Name | Meaning | Units | Normal range |
|---|---|---|---|
| `telemetry.oxy_pri_storage` | Primary O2 tank level ← **Sprint 0 value** | % | 20–100 |
| `telemetry.oxy_sec_storage` | Secondary O2 tank level | % | 20–100 |
| `telemetry.oxy_pri_pressure` | Primary O2 tank pressure | psi | 600–3000 |
| `telemetry.oxy_sec_pressure` | Secondary O2 tank pressure | psi | 600–3000 |
| `telemetry.oxy_consumption` | How fast O2 is being used | psi/min | 0.05–0.15 |
| `telemetry.suit_pressure_oxy` | O2 pressure inside the suit (target 4.0) | psi | 3.5–4.1 |

### Other suit data
| Name | Meaning | Units | Normal range |
|---|---|---|---|
| `telemetry.primary_battery_level` | Primary battery | % | 20–100 |
| `telemetry.secondary_battery_level` | Secondary battery | % | 20–100 |
| `telemetry.heart_rate` | Heart rate | bpm | 50–160 |
| `telemetry.temperature` | Temperature inside suit | °C | 10–32 |
| `telemetry.suit_pressure_co2` | CO2 pressure in suit | psi | 0–0.1 |
| `telemetry.helmet_pressure_co2` | CO2 pressure in helmet | psi | 0–0.15 |
| `telemetry.suit_pressure_total` | Total suit pressure | psi | 3.5–4.5 |
| `telemetry.scrubber_a_co2_storage` | CO2 scrubber A fill level (vent when > 60) | % | 0–60 |
| `telemetry.scrubber_b_co2_storage` | CO2 scrubber B fill level | % | 0–60 |
| `telemetry.fan_pri_rpm` / `fan_sec_rpm` | Fan speeds (should be 30,000) | rpm | 29,000–31,000 |
| `telemetry.coolant_storage` | Coolant level | % | 80–100 |
| `telemetry.eva_elapsed_time` | Time since EVA started | seconds | — |
| `status.started` | Has the EVA started? | true/false | — |
| `error.*` | Error flags: `fan_error`, `oxy_error`, `power_error`, `scrubber_error` | true/false | should be false |

Other `telemetry` values (`co2_production`, `suit_pressure_other`, coolant pressures) are listed in the NASA PDF.

### Switch positions
**DCU** (switch box on the suit). Tested by flipping each switch on the TSS web page and refreshing the JSON:
| Name | Web page switch | `true` | `false` |
|---|---|---|---|
| `dcu.batt.lu` | LOCAL / UMB battery | Local (suit battery) | Umbilical power |
| `dcu.batt.ps` | PRI / SEC battery | Primary battery | Secondary battery |
| `dcu.oxy` | O2 tank | Primary tank | Secondary tank |
| `dcu.fan` | Fan | Primary fan | Secondary fan |
| `dcu.pump` | Coolant pump | Open | Closed |
| `dcu.co2` | CO2 scrubber | Scrubber A | Scrubber B |

*(true/false meanings from NASA's README; confirmed that each switch flips its value.)*

**UIA** (wall panel used during egress). `true` = ON/OPEN, `false` = OFF/CLOSED:
| Name | Meaning |
|---|---|
| `uia.eva1_power` / `eva2_power` | Powers suit 1 / suit 2 |
| `uia.eva1_oxy` / `eva2_oxy` | Fills O2 tanks of suit 1 / 2 |
| `uia.eva1_water_supply` / `eva2_water_supply` | Fills coolant of suit 1 / 2 |
| `uia.eva1_water_waste` / `eva2_water_waste` | Flushes coolant of suit 1 / 2 |
| `uia.oxy_vent` | Empties both suits' O2 tanks |
| `uia.depress` | Depress pump: pressurizes suits |

### Astronaut location
| Name | Meaning |
|---|---|
| `imu.posx` | X position on the map |
| `imu.posy` | Y position on the map |
| `imu.heading` | Direction the astronaut faces (degrees) |

*(Coordinate units/origin: still to check against NASA's maps in `documents/maps`.)*

### Equipment groups (details later)
- `spec.eva1` / `spec.eva2`: rock scanner (spectrometer) result: rock name, type, and composition in %.
- `ssu.*`: Seismic Sensing Unit, a science payload deployed at a POI.

---

## 4. Fake equipment the TSS web page lets us control

We don't have NASA's physical hardware, but the TSS web page has virtual versions. **We don't need to build these ourselves.**

| What | On the web page |
|---|---|
| **Team selector** | Dropdown, teams 0–9 |
| **UIA panel** | All 10 UIA switches |
| **DCU** | All 6 DCU switches |
| **Spectrometer (rock scanner)** | Rock readings (`spec`); NASA includes a rock database in `data/RockData.json` (e.g. Mare Basalt) |
| **SSU (seismic sensor)** | Power and mode controls plus readings |
| **Errors** | Error flags (fan, O2, power, scrubber) |
| **Position** | Shows `imu` values |

Also useful:
- `scripts/simulate_position.py <server address>`: makes the astronaut "walk around" (fake GPS movement).
- `scripts/reset_data.bat`: resets all telemetry.

---

## Gotchas
- **The JSON in the browser doesn't update by itself.** Refresh it.
- **Wrong team = no changes.** The web page dropdown and the team in your URL/port must match.
- **Many values stay at 0 until the UIA egress steps are done** (e.g. `suit_pressure_oxy`). That's realistic, not a bug.
- **NASA says this is not the final TSS 2027 version.** Names could change. Check `documents/updates` in TSS2027 after a `git pull`.
