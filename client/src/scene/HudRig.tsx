// The rig that carries the panels. It sits at the head and turns to face where the head looks,
// with a delay, so a quick glance aside does not drag the panels along. It only turns about
// the up axis and never tilts. The arithmetic is in rigMath.ts.
import { useFrame } from "@react-three/fiber";
import { useRef, type ReactNode, type RefObject } from "react";
import { Vector3, type Group } from "three";
import { theme } from "../theme";
import { followYaw, headYaw } from "./rigMath";

const DEG = Math.PI / 180;
const headPosition = new Vector3();
const headDirection = new Vector3();

/** Set on the rig's userData once it has been placed at the head for the first time. */
export const RIG_PLACED = "placed";

export function HudRig({ children, rigRef, panelRef }: {
  children: ReactNode;
  rigRef: RefObject<Group | null>;
  /** The group at the panel's centre, for the view probe. */
  panelRef: RefObject<Group | null>;
}) {
  const yaw = useRef<number | null>(null);

  // In a WebXR session three.js moves this camera to the head pose on every render, so the
  // same code follows the fixed laptop camera and the wearer's head.
  useFrame(({ camera }, dtS) => {
    const rig = rigRef.current;
    if (rig === null) return;
    camera.getWorldPosition(headPosition);
    camera.getWorldDirection(headDirection);
    const target = headYaw(headDirection.x, headDirection.z, yaw.current ?? 0);
    yaw.current = yaw.current === null ? target : followYaw(yaw.current, target, dtS, theme.rig.followS);
    rig.position.copy(headPosition);
    rig.rotation.set(0, yaw.current, 0);
    rig.userData[RIG_PLACED] = true;
  });

  return (
    <group ref={rigRef}>
      <group rotation-y={theme.rig.panelYawDeg * DEG}>
        <group rotation-x={theme.rig.panelPitchDeg * DEG}>
          <group ref={panelRef} position-z={-theme.rig.distanceM}>
            {children}
          </group>
        </group>
      </group>
    </group>
  );
}
