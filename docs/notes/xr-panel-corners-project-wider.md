A panel turned to face the wearer reaches further out in a flat picture than its angles suggest, so check its corners by projection into each eye, not by adding angles.

Found in M2 (2026-11-24). A side panel at yaw 27°, pitch -18.5° looked fine by angles (bottom at -26°, laptop camera ±30° tall), but its outer bottom corner projected to 1.1× the picture's half-height: on a flat screen, y/z grows as 1/cos(yaw) away from the centre.

How the HUD checks it now (`client/src/hud/layout.ts`, tested in `layout.test.ts`):
- `cornerPoints` places the corners exactly as `scene/PanelAt.tsx` does (yaw, then pitch, then the panel distance).
- `reach(box, eye)` is how far out the panel lands in a picture: 1 is the edge. It is checked for the laptop camera (1280 x 720, `theme.camera.fovDeg`) and both emulated Quest 3 eyes (iwer: 90° tall, 640 x 720 per eye, eyes 32 mm from the centre), with a 2% margin.
- The far eye is the tight one: a panel on the right is cut first by the left eye.
- `ViewProbe` measures the same thing in the running page (`window.__hud.view.panelsOutOfView`), so the maths and the renderer are checked against each other.

The real Quest 3 sees wider than the emulator (about 110° across both eyes), so a layout that fits the emulator fits the headset; check again in M9.
