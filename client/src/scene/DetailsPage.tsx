// The details page: every telemetry value in groups, in two panels left and right of the clear
// centre. Shown while the backend says it is open (toggle_details).
import { Text } from "@react-three/uikit";
import type { DetailsGroup } from "../hud/types";
import type { PanelName } from "../hud/layout";
import { useHud } from "../store";
import { theme } from "../theme";
import { PanelAt } from "./PanelAt";
import { ValueLine } from "./ValueLine";

const { font, color } = theme;

function Column({ name, groups }: { name: PanelName; groups: DetailsGroup[] }) {
  return (
    <PanelAt name={name}>
      {groups.flatMap((group) => [
        <Text key={`title:${group.title}`} fontSize={font.label} fontWeight="bold" color={color.label}>
          {group.title}
        </Text>,
        ...group.rows.map((row) => <ValueLine key={row.name} row={row} />),
      ])}
    </PanelAt>
  );
}

export function DetailsPage() {
  const details = useHud((s) => s.panels.details);
  if (!details.open) return null;
  return (
    <>
      <Column name="detailsLeft" groups={details.columns[0]} />
      <Column name="detailsRight" groups={details.columns[1]} />
    </>
  );
}
