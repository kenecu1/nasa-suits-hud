# HUD Layout

Decided Oct 22, 2026 for SUITS-25 (app shell). This is the region plan every HUD feature plugs into.

## Sketch

```
┌──────────────────────────────────────────┐
│ BATTERY  ⚠ [ WARNING BANNER ] ⚠     MAP  │
│                               ┌────────┐ │
│ HEART                         │ Next:  │ │
│ RATE                          │ POI 2  │ │
│ (min,                         └────────┘ │
│ expands if high)    (clear view)         │
│                          O2 ▮▮▮▯  CO2 ↑  │
└──────────────────────────────────────────┘
At a POI: the mission tracker expands into the full procedure checklist
```

## Regions

| Region | Position | Behavior |
|---|---|---|
| Caution and warning | Top center | Static banner text so it reads instantly. A warning icon on each side flashes to catch peripheral vision. |
| Battery | Top left | Always visible, since it limits range. |
| Map | Top right | 2D mini map. Glanceable and out of the walking view. |
| Mission tracker | Below the map | Shows the current objective (e.g. "Next: POI 2") while traveling. |
| Procedures | Expands from the tracker | Full checklist, opened by click or by saying "show procedure". Optional hint pulses on arrival at a POI. |
| Heart rate | Left side | Minimized by default. Auto expands when it goes off nominal. |
| O2 | Bottom right | Segmented bar. Segments disappear as O2 is used. |
| CO2 | Bottom right | Smooth bar that rises, with an up arrow. |
| Center | Middle | Kept clear so the EV can see the ground. |

## Design reasons

- **Center stays clear:** the EV walks over rocks in low light, so nothing should block the ground.
- **Motion over brightness:** flashing icons instead of a bright full screen flash, to protect night vision.
- **Shape, not just color:** O2 segments and the CO2 arrow read correctly for color blind users and when colors wash out in low light.
- **Different shapes for different meanings:** O2 is a resource being spent (fewer segments = bad). CO2 is a hazard building up (higher bar = bad). The two can't be confused at a glance.
- **Threshold lines:** O2 and CO2 bars each get a line at the danger limit (values from `documents/telemetry_ranges/eva-telemetry-ranges.pdf`).
- **Two inputs for procedures:** voice works when hands are full of samples; click works when voice fails.
- **Video game quest pattern:** a small tracker while traveling, full checklist only at the station.
