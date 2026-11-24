// Lower right: consumables as bars, each with a mark at its warning limit.
import { Container, Text } from "@react-three/uikit";
import type { BarRow } from "../hud/types";
import { useHud } from "../store";
import { theme } from "../theme";
import { PanelAt } from "./PanelAt";
import { ValueLine } from "./ValueLine";

const { panel, font, color } = theme;

const percent = (fraction: number): `${number}%` => `${fraction * 100}%`;

function Bar({ row }: { row: BarRow }) {
  return (
    <Container width={panel.barWidth} height={panel.barHeight} flexShrink={0} backgroundColor={color.track}>
      <Container width={percent(row.fill)} height={panel.barHeight} backgroundColor={row.color} />
      {row.limit !== null && (
        <Container
          positionType="absolute"
          positionLeft={percent(row.limit)}
          positionTop={-panel.limitOverhang}
          width={panel.limitWidth}
          height={panel.barHeight + 2 * panel.limitOverhang}
          backgroundColor={color.text}
        />
      )}
    </Container>
  );
}

export function ConsumablesPanel() {
  const consumables = useHud((s) => s.panels.consumables);
  return (
    <PanelAt name="consumables">
      <Text fontSize={font.label} fontWeight="medium" color={color.label}>
        {consumables.label}
      </Text>
      {consumables.rows.map((row) => (
        <ValueLine key={row.name} row={row}>
          <Bar row={row} />
        </ValueLine>
      ))}
    </PanelAt>
  );
}
