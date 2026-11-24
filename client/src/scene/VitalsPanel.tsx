// Left: heart rate and temperature. A vital that is off-nominal is drawn larger.
import { Text } from "@react-three/uikit";
import { useHud } from "../store";
import { theme } from "../theme";
import { PanelAt } from "./PanelAt";
import { ValueLine } from "./ValueLine";

const { font, color } = theme;

export function VitalsPanel() {
  const vitals = useHud((s) => s.panels.vitals);
  return (
    <PanelAt name="vitals">
      <Text fontSize={font.label} fontWeight="medium" color={color.label}>
        {vitals.label}
      </Text>
      {vitals.rows.map((row) => (
        <ValueLine key={row.name} row={row} valueSize={row.grown ? font.vitalGrown : font.vital} />
      ))}
    </PanelAt>
  );
}
