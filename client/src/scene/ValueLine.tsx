// One value on one line: shape, label, number and the word the view model gives (none while
// nominal, see ValueRow.wordText).
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
    <Container flexDirection="row" alignItems="center" gap={panel.gap} flexShrink={0}>
      <LevelShape shape={row.shape} color={row.color} size={panel.shapeSize} />
      <Text fontSize={font.label} fontWeight="medium" color={color.label} flexGrow={1} flexShrink={1}>
        {row.label}
      </Text>
      {children}
      <Text fontSize={valueSize} fontWeight="bold" color={row.color}>
        {row.text}
      </Text>
      <Text fontSize={font.word} fontWeight="bold" color={row.color} width={panel.wordWidth} textAlign="right">
        {row.wordText}
      </Text>
    </Container>
  );
}
