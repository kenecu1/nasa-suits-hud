import { Canvas, useThree } from "@react-three/fiber";
import { useXR, XR } from "@react-three/xr";
import { useEffect, useRef, useState } from "react";
import type { Group } from "three";
import { XrButtons } from "../input/XrButtons";
import { SceneBoundary } from "../SceneBoundary";
import { useHud } from "../store";
import { theme } from "../theme";
import { AlertBanner } from "./AlertBanner";
import { ConsumablesPanel } from "./ConsumablesPanel";
import { DetailsPage } from "./DetailsPage";
import { HudRig } from "./HudRig";
import { PanelRegistryContext, type PanelRegistry } from "./PanelAt";
import { StatusPanel } from "./StatusPanel";
import { SwitchPanel } from "./SwitchPanel";
import { Tone } from "./Tone";
import { ViewProbe } from "./ViewProbe";
import { VitalsPanel } from "./VitalsPanel";
import { xrStore } from "./xr";

const { camera: cam } = theme;

/** Outside a session: a dark backdrop, and the camera back at its fixed place. */
function LaptopView() {
  const inSession = useXR((s) => s.session != null);
  const camera = useThree((s) => s.camera);
  useEffect(() => {
    if (inSession) return;
    camera.position.set(0, cam.eyeHeightM, 0);
    camera.rotation.set(0, 0, 0);
    camera.updateMatrixWorld();
  }, [inSession, camera]);
  return inSession ? null : <color attach="background" args={[theme.color.backdrop]} />;
}

function Hud() {
  const rigRef = useRef<Group>(null);
  const [registry] = useState<PanelRegistry>(() => new Map());
  // The details page takes the place of the vitals, switches and consumables (hud/layout.ts).
  const detailsOpen = useHud((s) => s.panels.details.open);
  return (
    <PanelRegistryContext.Provider value={registry}>
      <HudRig rigRef={rigRef}>
        <AlertBanner />
        <StatusPanel />
        {detailsOpen ? (
          <DetailsPage />
        ) : (
          <>
            <VitalsPanel />
            <SwitchPanel />
            <ConsumablesPanel />
          </>
        )}
      </HudRig>
      <ViewProbe rigRef={rigRef} registry={registry} />
      <Tone />
      <XrButtons />
    </PanelRegistryContext.Provider>
  );
}

export function HudScene({ onHudProblem }: { onHudProblem: (problem: string | null) => void }) {
  return (
    <Canvas
      camera={{ fov: cam.fovDeg, near: cam.near, far: cam.far, position: [0, cam.eyeHeightM, 0] }}
      gl={{ antialias: true, alpha: true }}
    >
      <XR store={xrStore}>
        <LaptopView />
        {/* Inside the canvas: if the HUD crashes, the renderer and a headset session live on. */}
        <SceneBoundary onProblem={onHudProblem}>
          <Hud />
        </SceneBoundary>
      </XR>
    </Canvas>
  );
}
