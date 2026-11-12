# M4 — Navigation

**Goal:** a 2D map with live position, breadcrumbs, pins and points of interest; a safe route to a target and back to the lander; a cue showing which way to walk. NASA requirements 2a, 4a, 4b, 4c, 5a.

**Builder:** Opus 5.5. **Fable review:** no.

**Read first:** `docs/walkthroughs/M3.md`; note `tss-map-coordinates`; decision 10 in `architecture.md`.

## Scope

0. **Inputs:** map images are in `vendor/TSS2027/documents/maps/`.
1. **Site data** (`data/mission/site.json`): map bounds, image transform (from two grid intersections), lander, points of interest, keep-out polygons, calibration defaults. NASA has not published FY27 points of interest: define a loop of 4 placeholder points inside the yard and mark them as ours. Trace keep-out polygons from `rock-yard-keep-out-zones.tiff`.
2. **Map image:** a script converts the TIFF to a web image of at most 1 MB in `client/public/map/`.
3. **Adapter:** add legacy command 5 (position and heading). Heading is degrees, 0 = map north, clockwise (our definition; the TSS has none).
4. **Navigation** (`core/nav.py`):
   - Position sources `tss` and `headset` behind one interface, chosen by `SUITS_POSITION_SOURCE` (default `tss`) and changeable with a `set_position_source` command. `headset` maps `pose` messages with a calibration (origin, heading offset, scale). A `calibrate` command sets the origin and heading to the lander's.
   - Breadcrumbs: one every 2 m moved, capped and thinned.
   - Pins: `drop_pin` at the current position, with a label and type.
   - Targets: `set_target` to a point of interest, a pin or the lander. Arrival within a radius from site data.
   - Route planner: A* on a 1 m grid, keep-out zones grown by a 2 m margin. Replan when more than 5 m off the route.
   - Return to lander: planned route; "backtrack" follows breadcrumbs in reverse.
   - Distance and time to arrive, with speed from the last 60 s (default 0.8 m/s, floor 0.3).
5. **Phase:** arrival at a point of interest sets `eva.phase` to `poi`; target lander sets `return`.
6. **Input:** `drop_pin`, `toggle_map`, `set_target`, `calibrate`, added to both binding tables.
7. **Panels:** mini-map (north-up, or heading-up by intent) with position and heading, breadcrumbs, pins, points of interest, keep-out shading and route; a navigation cue (bearing relative to heading, distance, time); a large map by `toggle_map`.

**Cut line:** if time is short, skip the A* planner and keep straight-line bearing plus breadcrumb backtrack.

## Acceptance

Backend (pytest)
1. World ↔ pixel transform: the two reference points round-trip within 1 pixel.
2. Breadcrumbs are 2 m apart on a straight walk and never exceed the cap. Pins can be added, renamed and removed.
3. Planner: no route point lies inside a grown keep-out zone; route length is within 10% of the known optimum on three small test maps; an enclosed target reports "no route"; planning on the full site grid takes under 200 ms.
4. From each point of interest the return route ends at the lander. Backtrack visits the breadcrumbs in reverse.
5. Headset source: after `calibrate`, a pose 1 m forward moves the position by `scale` metres along the calibrated heading. Heading follows yaw.
6. Time to arrive equals distance divided by speed, with the floor applied.
7. Scenario `traverse` (lander → point 1 → point 2 → lander): breadcrumbs grow, arrivals fire in order, a scripted detour triggers a replan, phases change as specified.

Client (vitest)
8. Navigation cue view model: a target dead ahead, 90° right, behind; distance and time formatting.
9. Map view model: world to panel coordinates for both north-up and heading-up.

End to end (Playwright)
10. Desktop: map screenshot with route, pins and keep-out zones. `drop_pin` by key adds a pin at the current position.
11. Emulated headset, backend started with `SUITS_POSITION_SOURCE=headset`: after `calibrate`, moving the emulated headset 1 m moves the map marker by the configured scale.
