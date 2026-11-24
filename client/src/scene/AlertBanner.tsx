// The alert banner, top centre: up to three alerts with their actions, plus "+N MORE".
// Draws hud/banner.vm.ts and nothing else; acknowledging is an intent (input/), not a click here.
import { Container, Text } from "@react-three/uikit";
import { useHud } from "../store";
import { theme } from "../theme";
import { LevelShape } from "./LevelShape";
import { PanelAt } from "./PanelAt";

const { panel, font, color } = theme;

export function AlertBanner() {
  const banner = useHud((s) => s.panels.banner);
  if (!banner.visible) return null;
  return (
    <PanelAt name="banner" fitHeight>
      {banner.rows.map((row) => (
        <Container key={row.id} flexDirection="column" paddingBottom={panel.rowGap}>
          <Container flexDirection="row" alignItems="center" gap={panel.gap}>
            <LevelShape shape={row.shape} color={row.color} size={panel.shapeSize} />
            <Text fontSize={font.word} fontWeight="bold" color={row.color}>
              {row.word}
            </Text>
            <Text fontSize={font.title} fontWeight="bold" color={row.color} flexGrow={1} flexShrink={1}>
              {row.title}
            </Text>
            <Text fontSize={font.word} fontWeight="medium" color={color.label}>
              {row.ackText}
            </Text>
          </Container>
          <Text fontSize={font.row} color={row.actionColor}>
            {row.action}
          </Text>
        </Container>
      ))}
      {banner.moreText !== null && (
        <Text fontSize={font.row} fontWeight="medium" color={color.label}>
          {banner.moreText}
        </Text>
      )}
    </PanelAt>
  );
}
