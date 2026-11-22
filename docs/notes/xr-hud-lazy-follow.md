The HUD rig lags behind the head and turns only left/right. It is not locked to the head, so the panel slides and catches up when you turn, and leaves view when you look up or down.

Built in M1 (`client/src/scene/HudRig.tsx`, `rigMath.ts`, numbers in `theme.ts` under `rig`):
- Each frame the rig moves to the head's position and turns toward the head's yaw with an exponential follow. `followS` 0.35 s closes about 63% of the gap in that time, whatever the frame rate.
- Pitch and roll are not followed. The panel sits 1.2 m away, 15° right and 11° below the horizon. Those angles are measured from the horizon, not from your gaze.
- On the laptop page the camera is fixed at eye height and nothing moves. Only an XR session (real or emulated) moves the camera.
- The headset test checks both halves: right after a 90° turn the panel is briefly out of view, and 2 s later it is back in view.

Why: a panel glued to the face is tiring, jitters with every small head movement and covers the centre of view. Lag plus yaw-only is the usual "tag-along" HUD. If a value must always be visible, tune `rig` in `theme.ts` (a smaller `followS`), not the component.
