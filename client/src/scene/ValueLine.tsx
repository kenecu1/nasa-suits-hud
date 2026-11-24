// One value on one line: shape, label, number and, when it is not nominal, the level's word.
// Nominal shows no word: seven green "NOMINAL"s would be noise in a dim helmet; its circle and
// colour still say it, and every other level adds its word.
import { Container, Text } from "@react-three/uikit";
import type { ReactNode } from "react";
import type { ValueRow } from "../hud/types";
import { theme } from "../theme";
import { LevelShape } from "./LevelShape";

const { panel, font, color } = theme;

export function ValueLine({ row, valueSize = font.row, children }: {
  row: ValueRow;
  valueSize?: number;
  /** Drawn between the label and the number (a consumables bar). */
  children?: ReactNode;
}) {
  return (
    <Container flexDirection="row" alignItems="center" gap={panel.gap}>
      <LevelShape shape={row.shape} color={row.color} size={panel.shapeSize} />
      <Text fontSize={font.label} fontWeight="medium" color={color.label} flexGrow={1} flexShrink={1}>
        {row.label}
      </Text>
      {children}
      <Text fontSize={valueSize} fontWeight="bold" color={row.color}>
        {row.text}
      </Text>
      <Text fontSize={font.word} fontWeight="bold" color={row.color} width={panel.wordWidth} textAlign="right">
        {row.level === "nominal" ? "" : row.word}
      </Text>
    </Container>
  );
}
