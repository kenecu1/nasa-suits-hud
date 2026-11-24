// The details page: every telemetry value, in groups, in two columns. Opened and closed by
// the backend (`ui.details_open`, changed by the toggle_details command).
import type { State } from "../contract.gen";
import type { Conn, DetailsGroup, DetailsVm } from "./types";
import { valueRow } from "./values";

interface GroupSpec {
  title: string;
  names: readonly string[];
}

export const DETAILS_COLUMNS: readonly [readonly GroupSpec[], readonly GroupSpec[]] = [
  [
    {
      title: "OXYGEN",
      names: ["oxy_pri_storage", "oxy_sec_storage", "oxy_pri_pressure", "oxy_sec_pressure", "oxy_consumption"],
    },
    { title: "POWER", names: ["primary_battery_level", "secondary_battery_level"] },
    {
      title: "SUIT",
      names: [
        "suit_pressure_oxy",
        "suit_pressure_co2",
        "suit_pressure_other",
        "suit_pressure_total",
        "helmet_pressure_co2",
        "co2_production",
      ],
    },
  ],
  [
    { title: "FANS", names: ["fan_pri_rpm", "fan_sec_rpm"] },
    { title: "SCRUBBERS", names: ["scrubber_a_co2_storage", "scrubber_b_co2_storage"] },
    { title: "COOLING", names: ["coolant_storage", "coolant_liquid_pressure", "coolant_gas_pressure"] },
    { title: "BODY", names: ["heart_rate", "temperature", "eva_elapsed_time"] },
  ],
];

const KNOWN = new Set(DETAILS_COLUMNS.flat().flatMap((g) => g.names));

export function detailsVm(state: State | null, conn: Conn): DetailsVm {
  const group = ({ title, names }: GroupSpec): DetailsGroup => ({
    title,
    rows: names.map((name) => valueRow(state, name, conn)),
  });
  const left = DETAILS_COLUMNS[0].map(group);
  const right = DETAILS_COLUMNS[1].map(group);
  // A value this page does not list (a newer backend) is shown under OTHER, never hidden.
  const values = state?.suit.values ?? {};
  const others = Object.keys(values)
    .filter((name) => !KNOWN.has(name))
    .sort();
  if (others.length > 0) right.push(group({ title: "OTHER", names: others }));
  const columns: [DetailsGroup[], DetailsGroup[]] = [left, right];
  return {
    open: state?.ui?.details_open === true,
    columns,
    names: columns.flat().flatMap((g) => g.rows.map((r) => r.name)),
  };
}
