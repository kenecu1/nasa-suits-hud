// One panel on the rig: placed at its box from hud/layout.ts, with the dark translucent backing,
// and registered so the view probe can check its corners.
import { Container, withOpacity } from "@react-three/uikit";
import { createContext, useCallback, useContext, type ReactNode } from "react";
import type { Group } from "three";
import { LAYOUT, type PanelName } from "../hud/layout";
import { theme } from "../theme";

const DEG = Math.PI / 180;

/** The panels drawn right now, by name. ViewProbe reads it once a frame. */
export type PanelRegistry = Map<PanelName, Group>;

export const PanelRegistryContext = createContext<PanelRegistry | null>(null);

const { panel, color } = theme;

export function PanelAt({ name, children, fitHeight = false }: {
  name: PanelName;
  children: ReactNode;
  /** Size to the content instead of the box (the banner); the box stays the most it can take. */
  fitHeight?: boolean;
}) {
  const registry = useContext(PanelRegistryContext);
  const box = LAYOUT[name];
  const register = useCallback(
    (group: Group | null) => {
      if (registry === null) return undefined;
      if (group === null) return undefined;
      registry.set(name, group);
      return () => {
        if (registry.get(name) === group) registry.delete(name);
      };
    },
    [registry, name],
  );
  return (
    <group rotation-y={box.yawDeg * DEG}>
      <group rotation-x={box.pitchDeg * DEG}>
        <group ref={register} position-z={-theme.rig.distanceM}>
          <Container
            pixelSize={panel.pixelSize}
            anchorY={box.anchor === "top" ? "top" : "center"}
            width={box.widthPx}
            height={fitHeight ? undefined : box.heightPx}
            maxHeight={box.heightPx}
            overflow="hidden"
            flexDirection="column"
            padding={panel.padding}
            gap={panel.rowGap}
            borderRadius={panel.radius}
            backgroundColor={withOpacity(color.panel, panel.opacity)}
          >
            {children}
          </Container>
        </group>
      </group>
    </group>
  );
}
