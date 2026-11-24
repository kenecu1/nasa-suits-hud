import { describe, expect, it } from "vitest";
import type { DcuPositions, State, UiaPositions } from "../contract.gen";
import { theme } from "../theme";
import { deepFreeze, loose, makeState } from "./testState";
import { switchesVm } from "./switches.vm";
import type { Conn } from "./types";

const DCU_LABELS = ["BATT", "OXY", "COMM", "FAN", "PUMP", "CO2"];
const UIA_LABELS = ["PWR", "O2", "H2O", "WASTE", "VENT", "DEPR"];

const DCU_ALL: [keyof DcuPositions, string, string, string][] = [
  ["batt", "BATT", "UMB", "LOCAL"],
  ["oxy", "OXY", "PRI", "SEC"],
  ["comm", "COMM", "A", "B"],
  ["fan", "FAN", "PRI", "SEC"],
  ["pump", "PUMP", "OPEN", "CLOSED"],
  ["co2", "CO2", "A", "B"],
];

const UIA_ALL: [keyof UiaPositions, string, string, string][] = [
  ["eva_power", "PWR", "ON", "OFF"],
  ["o2_supply", "O2", "OPEN", "CLOSED"],
  ["water_supply", "H2O", "OPEN", "CLOSED"],
  ["water_waste", "WASTE", "OPEN", "CLOSED"],
  ["o2_vent", "VENT", "OPEN", "CLOSED"],
  ["depress", "DEPR", "OPEN", "CLOSED"],
];

const dcuWith = (key: keyof DcuPositions, value: unknown): State =>
  makeState({ dcu: loose<DcuPositions>({ ...makeState().dcu, [key]: value }) });
const uiaWith = (key: keyof UiaPositions, value: unknown): State =>
  makeState({ uia: loose<UiaPositions>({ ...makeState().uia, [key]: value }) });

describe("switchesVm", () => {
  it("labels the two blocks DCU and UIA", () => {
    const vm = switchesVm(makeState(), "live");
    expect(vm.dcu.label).toBe("DCU");
    expect(vm.uia.label).toBe("UIA");
  });

  it("has the six DCU rows and the six UIA rows in order", () => {
    const vm = switchesVm(makeState(), "live");
    expect(vm.dcu.rows.map((r) => r.label)).toEqual(DCU_LABELS);
    expect(vm.uia.rows.map((r) => r.label)).toEqual(UIA_LABELS);
  });

  it.each(DCU_ALL.flatMap(([key, label, a, b]) => [[key, label, a], [key, label, b]] as const))(
    "shows DCU %s (%s) at %s, current, in the text colour",
    (key, label, position) => {
      const vm = switchesVm(dcuWith(key, position), "live");
      const row = vm.dcu.rows.find((r) => r.label === label);
      expect(row).toEqual({ label, text: position, current: true, color: theme.color.text });
    },
  );

  it.each(UIA_ALL.flatMap(([key, label, a, b]) => [[key, label, a], [key, label, b]] as const))(
    "shows UIA %s (%s) at %s, current, in the text colour",
    (key, label, position) => {
      const vm = switchesVm(uiaWith(key, position), "live");
      const row = vm.uia.rows.find((r) => r.label === label);
      expect(row).toEqual({ label, text: position, current: true, color: theme.color.text });
    },
  );

  it("shows -- with the unknown colour for every DCU row when dcu is null", () => {
    const vm = switchesVm(makeState({ dcu: null }), "live");
    expect(vm.dcu.rows.map((r) => r.label)).toEqual(DCU_LABELS);
    for (const row of vm.dcu.rows) expect(row).toMatchObject({ text: "--", current: false, color: theme.level.unknown.color });
  });

  it("shows -- with the unknown colour for every UIA row when uia is null, and still shows the DCU", () => {
    const vm = switchesVm(makeState({ uia: null }), "live");
    for (const row of vm.uia.rows) expect(row).toMatchObject({ text: "--", current: false, color: theme.level.unknown.color });
    expect(vm.dcu.rows.every((r) => r.current)).toBe(true);
  });

  it("shows -- everywhere without a state", () => {
    const vm = switchesVm(null, "connecting");
    for (const row of [...vm.dcu.rows, ...vm.uia.rows]) {
      expect(row).toMatchObject({ text: "--", current: false, color: theme.level.unknown.color });
    }
  });

  it.each<Conn>(["offline", "connecting"])("keeps the text, is not current, and has the stale colour when conn is %s", (conn) => {
    const vm = switchesVm(makeState(), conn);
    const rows = [...vm.dcu.rows, ...vm.uia.rows];
    expect(vm.dcu.rows[1]).toMatchObject({ label: "OXY", text: "PRI" });
    for (const row of rows) expect(row).toMatchObject({ current: false, color: theme.level.stale.color });
    expect(rows.every((r) => r.text !== "--")).toBe(true);
  });

  it("keeps -- unknown (not stale) for a missing block when offline", () => {
    const vm = switchesVm(makeState({ dcu: null }), "offline");
    for (const row of vm.dcu.rows) expect(row).toMatchObject({ text: "--", current: false, color: theme.level.unknown.color });
  });

  it.each<[string, unknown]>([
    ["a word the contract does not name", "BOGUS"],
    ["a number", 3],
    ["null", null],
    ["a position of another switch", "OPEN"],
    ["lower case", "pri"],
    ["an inherited key", "toString"],
  ])("shows -- for the DCU oxy switch at %s", (_what, value) => {
    const vm = switchesVm(dcuWith("oxy", value), "live");
    expect(vm.dcu.rows[1]).toEqual({ label: "OXY", text: "--", current: false, color: theme.level.unknown.color });
  });

  it("shows -- for a UIA switch at a position the contract does not name", () => {
    const vm = switchesVm(uiaWith("eva_power", "OPEN"), "live");
    expect(vm.uia.rows[0]).toEqual({ label: "PWR", text: "--", current: false, color: theme.level.unknown.color });
  });

  it("shows -- for a switch the state leaves out, and only that switch", () => {
    const dcu = { ...makeState().dcu } as Partial<DcuPositions>;
    delete dcu.pump;
    const vm = switchesVm(makeState({ dcu: loose<DcuPositions>(dcu) }), "live");
    expect(vm.dcu.rows.map((r) => r.text)).toEqual(["LOCAL", "PRI", "A", "PRI", "--", "A"]);
  });

  it("does not read a switch from the prototype (dcu is an empty object)", () => {
    const vm = switchesVm(makeState({ dcu: loose<DcuPositions>({}) }), "live");
    for (const row of vm.dcu.rows) expect(row.text).toBe("--");
  });

  it("does not change its input", () => {
    expect(() => switchesVm(deepFreeze(makeState()), "live")).not.toThrow();
  });
});
