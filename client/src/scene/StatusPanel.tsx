// The one M1 panel: primary oxygen, the DCU oxygen switch and the link. It draws the view
// models and decides nothing: every word, colour and shape comes from client/src/hud/.
import { Container, Text, withOpacity } from "@react-three/uikit";
import { useHud } from "../store";
import { theme } from "../theme";
import { LevelShape } from "./LevelShape";

const { panel, font, color } = theme;

export function StatusPanel() {
  const { o2, dcu, link } = useHud((s) => s.panels);

  return (
    <Container
      pixelSize={panel.pixelSize}
      width={panel.width}
      height={panel.height}
      flexDirection="column"
      justifyContent="space-between"
      padding={panel.padding}
      borderRadius={panel.radius}
      backgroundColor={withOpacity(color.panel, panel.opacity)}
    >
      <Container flexDirection="column" gap={panel.gap}>
        <Text fontSize={font.label} fontWeight="medium" color={color.label}>
          {o2.label}
        </Text>
        <Container flexDirection="row" alignItems="center" gap={panel.gap}>
          <LevelShape shape={o2.shape} color={o2.color} size={panel.shapeSize} />
          <Text fontSize={font.value} fontWeight="bold" color={o2.color}>
            {o2.text}
          </Text>
          <Text fontSize={font.word} fontWeight="bold" color={o2.color}>
            {o2.word}
          </Text>
        </Container>
      </Container>

      <Container flexDirection="column" gap={panel.rowGap}>
        <Container flexDirection="row" alignItems="center" justifyContent="space-between">
          <Text fontSize={font.label} fontWeight="medium" color={color.label}>
            {dcu.label}
          </Text>
          <Text fontSize={font.row} fontWeight="bold" color={dcu.color}>
            {dcu.text}
          </Text>
        </Container>
        <Container flexDirection="row" alignItems="center" gap={panel.gap}>
          <Text fontSize={font.label} fontWeight="medium" color={color.label}>
            {link.label}
          </Text>
          <LevelShape shape={link.shape} color={link.color} size={panel.smallShapeSize} />
          <Text fontSize={font.row} fontWeight="bold" color={link.color} flexGrow={1}>
            {link.text}
          </Text>
          <Text fontSize={font.label} fontWeight="medium" color={color.label}>
            {link.mode ?? ""}
          </Text>
        </Container>
      </Container>
    </Container>
  );
}
