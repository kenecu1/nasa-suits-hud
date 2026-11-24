// Lower left: DCU and UIA switch positions, side by side.
import { Container, Text } from "@react-three/uikit";
import type { SwitchRow } from "../hud/types";
import { useHud } from "../store";
import { theme } from "../theme";
import { PanelAt } from "./PanelAt";

const { panel, font, color } = theme;

function Column({ label, rows }: { label: string; rows: SwitchRow[] }) {
  return (
    <Container flexDirection="column" flexGrow={1} flexBasis={0} gap={panel.rowGap}>
      <Text fontSize={font.label} fontWeight="bold" color={color.label}>
        {label}
      </Text>
      {rows.map((row) => (
        <Container key={row.label} flexDirection="row" justifyContent="space-between" gap={panel.gap}>
          <Text fontSize={font.label} fontWeight="medium" color={color.label}>
            {row.label}
          </Text>
          <Text fontSize={font.row} fontWeight="bold" color={row.color}>
            {row.text}
          </Text>
        </Container>
      ))}
    </Container>
  );
}

export function SwitchPanel() {
  const { dcu, uia } = useHud((s) => s.panels.switches);
  return (
    <PanelAt name="switches">
      <Container flexDirection="row" gap={panel.columnGap}>
        <Column label={dcu.label} rows={dcu.rows} />
        <Column label={uia.label} rows={uia.rows} />
      </Container>
    </PanelAt>
  );
}
