// Top left: the EVA clock and the link line.
import { Container, Text } from "@react-three/uikit";
import { useHud } from "../store";
import { theme } from "../theme";
import { LevelShape } from "./LevelShape";
import { PanelAt } from "./PanelAt";

const { panel, font, color } = theme;

export function StatusPanel() {
  const clock = useHud((s) => s.panels.clock);
  const link = useHud((s) => s.panels.link);
  return (
    <PanelAt name="status">
      <Container flexDirection="row" alignItems="center" gap={panel.gap}>
        <Text fontSize={font.label} fontWeight="medium" color={color.label}>
          {clock.label}
        </Text>
        <Text fontSize={font.title} fontWeight="bold" color={clock.color}>
          {clock.text}
        </Text>
      </Container>
      <Container flexDirection="row" alignItems="center" gap={panel.gap}>
        <Text fontSize={font.label} fontWeight="medium" color={color.label}>
          {link.label}
        </Text>
        <LevelShape shape={link.shape} color={link.color} size={panel.shapeSize} />
        <Text fontSize={font.row} fontWeight="bold" color={link.color} flexGrow={1} flexShrink={1}>
          {link.text}
        </Text>
        <Text fontSize={font.label} fontWeight="medium" color={color.label}>
          {link.mode ?? ""}
        </Text>
      </Container>
    </PanelAt>
  );
}
