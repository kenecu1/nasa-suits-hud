import { describe, expect, it } from "vitest";
import ranges from "../../../data/ranges.json";
import type { State } from "../contract.gen";
import { theme } from "../theme";
import { DETAILS_COLUMNS, detailsVm } from "./details.vm";
import { deepFreeze, loose, makeState, makeValue, withValue } from "./testState";
import type { Conn } from "./types";

const ALL_NAMES = [...Object.keys(ranges.ranges), ...Object.keys(ranges.unranged)].sort();

function rowOf(vm: ReturnType<typeof detailsVm>, name: string) {
  for (const column of vm.columns) {
    for (const group of column) {
      const found = group.rows.find((r) => r.name === name);
      if (found !== undefined) return found;
    }
  }
  throw new Error(`no row for ${name}`);
}

describe("detailsVm", () => {
  it("knows 23 telemetry names (22 ranged and 1 unranged)", () => {
    expect(ALL_NAMES).toHaveLength(23);
    expect(Object.keys(makeState().suit.values).sort()).toEqual(ALL_NAMES);
  });

  it("lists every name of the state exactly once", () => {
    const state = makeState();
    const vm = detailsVm(state, "live");
    expect([...vm.names].sort()).toEqual(Object.keys(state.suit.values).sort());
    expect([...vm.names].sort()).toEqual(ALL_NAMES);
    expect(new Set(vm.names).size).toBe(vm.names.length);
  });

  it("lists every name even without a state, with -- as text", () => {
    const vm = detailsVm(null, "connecting");
    expect([...vm.names].sort()).toEqual(ALL_NAMES);
    for (const column of vm.columns) for (const group of column) for (const r of group.rows) expect(r).toMatchObject({ text: "--", level: "unknown" });
  });

  it("has two columns, with the names in page order", () => {
    const vm = detailsVm(makeState(), "live");
    expect(vm.columns).toHaveLength(2);
    expect(vm.names).toEqual(vm.columns.flat().flatMap((g) => g.rows.map((r) => r.name)));
    expect(vm.columns[0].map((g) => g.title)).toEqual(["OXYGEN", "POWER", "SUIT"]);
    expect(vm.columns[1].map((g) => g.title)).toEqual(["FANS", "SCRUBBERS", "COOLING", "BODY"]);
  });

  it("keeps the page layout in sync with the list of names (DETAILS_COLUMNS)", () => {
    expect(DETAILS_COLUMNS.flat().flatMap((g) => g.names).sort()).toEqual(ALL_NAMES);
  });

  it("has no OTHER group when every value is known", () => {
    const vm = detailsVm(makeState(), "live");
    expect(vm.columns.flat().some((g) => g.title === "OTHER")).toBe(false);
  });

  describe("open", () => {
    it.each([true, false])("follows ui.details_open (%s)", (open) => {
      expect(detailsVm(makeState({ ui: { details_open: open } }), "live").open).toBe(open);
    });

    it("is closed without a state", () => {
      expect(detailsVm(null, "connecting").open).toBe(false);
    });

    it("is closed when ui is missing or not exactly true", () => {
      expect(detailsVm(loose<State>({ ...makeState(), ui: undefined }), "live").open).toBe(false);
      expect(detailsVm(loose<State>({ ...makeState(), ui: { details_open: "yes" } }), "live").open).toBe(false);
    });

    it("stays open when offline, because the page shows the last state", () => {
      expect(detailsVm(makeState({ ui: { details_open: true } }), "offline").open).toBe(true);
    });
  });

  describe("a name the page does not list", () => {
    const extra = withValue("zz_new_sensor", makeValue(1.5, "caution", "kg"));

    it("appears in an OTHER group at the end of the right column", () => {
      const vm = detailsVm(extra, "live");
      const last = vm.columns[1].at(-1);
      expect(last?.title).toBe("OTHER");
      expect(last?.rows).toHaveLength(1);
      expect(last?.rows[0]).toMatchObject({ name: "zz_new_sensor", label: "ZZ_NEW_SENSOR", text: "1.50 kg", level: "caution" });
      expect(vm.columns[0].some((g) => g.title === "OTHER")).toBe(false);
    });

    it("is in names, once, together with the 23 known ones", () => {
      const vm = detailsVm(extra, "live");
      expect([...vm.names].sort()).toEqual([...ALL_NAMES, "zz_new_sensor"].sort());
      expect(vm.names.filter((n) => n === "zz_new_sensor")).toHaveLength(1);
    });

    it("sorts several unknown names", () => {
      const state = withValue("b_extra", makeValue(2, "nominal", ""), withValue("a_extra", makeValue(1, "nominal", ""), extra));
      const other = detailsVm(state, "live").columns[1].at(-1);
      expect(other?.rows.map((r) => r.name)).toEqual(["a_extra", "b_extra", "zz_new_sensor"]);
    });

    it("does not break the known groups", () => {
      const vm = detailsVm(extra, "live");
      expect(vm.columns[0].map((g) => g.title)).toEqual(["OXYGEN", "POWER", "SUIT"]);
      expect(vm.columns[1].map((g) => g.title)).toEqual(["FANS", "SCRUBBERS", "COOLING", "BODY", "OTHER"]);
    });

    it("is drawn stale when offline", () => {
      const other = detailsVm(extra, "offline").columns[1].at(-1);
      expect(other?.rows[0]).toMatchObject({ level: "stale", text: "1.50 kg" });
    });
  });

  it("shows a missing known value as -- with the unknown look, keeping its row", () => {
    const state = withValue("heart_rate", undefined);
    const vm = detailsVm(state, "live");
    expect(rowOf(vm, "heart_rate")).toMatchObject({ text: "--", level: "unknown", ...theme.level.unknown });
    expect([...vm.names].sort()).toEqual(ALL_NAMES);
  });

  it("shows fan_sec_rpm at level off as OFF with the dash shape", () => {
    const vm = detailsVm(makeState(), "live");
    expect(rowOf(vm, "fan_sec_rpm")).toMatchObject({ level: "off", word: "OFF", shape: "dash", color: theme.level.off.color });
  });

  it("shows the off fan as stale when offline", () => {
    expect(rowOf(detailsVm(makeState(), "offline"), "fan_sec_rpm")).toMatchObject({ level: "stale", word: "STALE", shape: "square" });
  });

  it("writes the EVA time as h:mm:ss in the BODY group", () => {
    const vm = detailsVm(makeState(), "live");
    const body = vm.columns[1].find((g) => g.title === "BODY");
    expect(body?.rows.find((r) => r.name === "eva_elapsed_time")?.text).toBe("00:21:52");
  });

  it.each<Conn>(["offline", "connecting"])("draws every row with a number stale when conn is %s", (conn) => {
    const vm = detailsVm(makeState(), conn);
    for (const column of vm.columns) for (const group of column) for (const r of group.rows) expect(r.level).toBe("stale");
  });

  it("does not change its input", () => {
    const state = deepFreeze(withValue("zz_new_sensor", makeValue(1, "nominal", "x")));
    expect(() => detailsVm(state, "live")).not.toThrow();
  });
});
