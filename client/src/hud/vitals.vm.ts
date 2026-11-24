// Vitals, left: heart rate and temperature, small while nominal and larger while off-nominal.
import type { State } from "../contract.gen";
import type { Conn, VitalsVm } from "./types";
import { valueRow } from "./values";

export const VITALS: readonly string[] = ["heart_rate", "temperature"];

export function vitalsVm(state: State | null, conn: Conn): VitalsVm {
  return {
    label: "VITALS",
    rows: VITALS.map((name) => {
      const row = valueRow(state, name, conn);
      return { ...row, grown: row.level === "caution" || row.level === "warning" };
    }),
  };
}
