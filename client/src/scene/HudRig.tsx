import { useFrame } from "@react-three/fiber";
import { useRef, type ReactNode, type RefObject } from "react";
import { Vector3, type Group } from "three";
import { theme } from "../theme";
import { followYaw, headYaw } from "./rigMath";

const headPosition = new Vector3();
const headDirection = new Vector3();

/** Set on the rig's userData once it has been placed at the head for the first time. */
export const RIG_PLACED = "placed";

/**
 * Carries the panels: it sits at the head, follows the head's yaw with a delay and never tilts
 * (docs/notes/xr-hud-lazy-follow.md). Each panel places itself on it (PanelAt, hud/layout.ts).
 */
export function HudRig({ children, rigRef }: { children: ReactNode; rigRef: RefObject<Group | null> }) {
  const yaw = useRef<number | null>(null);

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

  return <group ref={rigRef}>{children}</group>;
}
