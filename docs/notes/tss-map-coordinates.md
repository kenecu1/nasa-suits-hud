The rock-yard map uses metres with X from −5760 to −5550 and Y from −10070 to −9940; the lander (HAB) is at (−5670, −10060). These come from 2025-26 documents and may change.

Source: `documents/maps/` and `documents/procedures/ev-team-coordinates.pdf` in TSS2027 (dated March 2026).

- `maps/annotated/rock-yard.tiff` — 3800×2486 RGBA, greyscale aerial image with a 10 m grid and axis labels. The image has margins: derive the pixel-to-metre transform from two grid intersections, not from the image corners.
- `maps/annotated/rock-yard-keep-out-zones.tiff` — 3907×2578, same view with exclusion zones drawn. Different pixel size from the plain map, so it needs its own transform.
- `maps/raw/rock-yard.tiff` — 3507×2220, raw imagery.
- `3d-scans/lunar.obj` — 14 MB, 77k vertices, about ±27 m × ±28 m, height ±0.87 m. Its own local frame, not map coordinates. The material file it names is missing.
- Known points (accurate to about 10 m): HAB (−5670, −10060), LTV Task Board Alpha (−5635, −9970), Bravo (−5615, −9995). FY27 replaces the LTV tasks with POIs in a loop; their coordinates are not published yet.
- TSS `imu` gives `posx`, `posy`, `heading` in this frame. The TSS source does not define the heading convention. Ours: degrees, 0 = map north (+Y), clockwise.

Keep map bounds, the image transform, POIs and keep-out polygons in one data file (`data/mission/site.json`), not in code.
