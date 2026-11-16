// The one scene, drawn in three places: the laptop page (fixed camera, dark backdrop), the
// emulated headset and the real headset (the camera is the head, the background is the world).
import { Canvas, useThree } from "@react-three/fiber";
import { useXR, XR } from "@react-three/xr";
import { useEffect, useRef } from "react";
import type { Group } from "three";
import { theme } from "../theme";
import { HudRig } from "./HudRig";
import { StatusPanel } from "./StatusPanel";
import { ViewProbe } from "./ViewProbe";
import { xrStore } from "./xr";

const { camera: cam } = theme;

/** Outside a session: a dark backdrop, and the camera back at its fixed place. */
function LaptopView() {
  const inSession = useXR((s) => s.session != null);
  const camera = useThree((s) => s.camera);

  useEffect(() => {
    if (inSession) return;
    // A session leaves the camera wherever the head was.
    camera.position.set(0, cam.eyeHeightM, 0);
    camera.rotation.set(0, 0, 0);
    camera.updateMatrixWorld();
  }, [inSession, camera]);

  return inSession ? null : <color attach="background" args={[theme.color.backdrop]} />;
}

function Hud() {
  const rigRef = useRef<Group>(null);
  const panelRef = useRef<Group>(null);
  return (
    <>
      <HudRig rigRef={rigRef} panelRef={panelRef}>
        <StatusPanel />
      </HudRig>
      <ViewProbe rigRef={rigRef} panelRef={panelRef} />
    </>
  );
}

export function HudScene() {
  return (
    <Canvas
      camera={{ fov: cam.fovDeg, near: cam.near, far: cam.far, position: [0, cam.eyeHeightM, 0] }}
      gl={{ antialias: true, alpha: true }}
    >
      <XR store={xrStore}>
        <LaptopView />
        <Hud />
      </XR>
    </Canvas>
  );
}
