import { describe, expect, it } from "vitest";
import type { Alert, State } from "../contract.gen";
import { theme } from "../theme";
import { BANNER_ROWS, bannerVm } from "./banner.vm";
import { deepFreeze, loose, makeAlert, makeState } from "./testState";
import type { Conn } from "./types";

const stateWith = (alerts: Alert[]): State => makeState({ alerts });
const ids = (count: number): Alert[] => Array.from({ length: count }, (_, i) => makeAlert(`a${i + 1}`, i % 2 === 0 ? "warning" : "caution"));

describe("bannerVm", () => {
  it("shows at most three rows", () => {
    expect(BANNER_ROWS).toBe(3);
  });

  it("is not visible and has no top id without alerts", () => {
    expect(bannerVm(stateWith([]), "live")).toEqual({ rows: [], more: 0, moreText: null, topId: null, visible: false });
  });

  it("is not visible without a state", () => {
    expect(bannerVm(null, "connecting")).toEqual({ rows: [], more: 0, moreText: null, topId: null, visible: false });
  });

  it("is not visible when the state has no alerts list at all", () => {
    const state = loose<State>({ ...makeState(), alerts: undefined });
    expect(bannerVm(state, "live").visible).toBe(false);
  });

  it.each([1, 2, 3])("shows %s alerts as that many rows and no +N MORE", (count) => {
    const vm = bannerVm(stateWith(ids(count)), "live");
    expect(vm.rows).toHaveLength(count);
    expect(vm.more).toBe(0);
    expect(vm.moreText).toBeNull();
    expect(vm.visible).toBe(true);
  });

  it("keeps the backend's order and does not sort", () => {
    const alerts = [
      makeAlert("c-first", "caution"),
      makeAlert("w-second", "warning"),
      makeAlert("c-third", "caution"),
    ];
    expect(bannerVm(stateWith(alerts), "live").rows.map((r) => r.id)).toEqual(["c-first", "w-second", "c-third"]);
  });

  it("takes colour, shape and word of each row from theme.level[severity]", () => {
    const vm = bannerVm(stateWith([makeAlert("w", "warning"), makeAlert("c", "caution")]), "live");
    expect(vm.rows[0]).toMatchObject({ level: "warning", ...theme.level.warning });
    expect(vm.rows[1]).toMatchObject({ level: "caution", ...theme.level.caution });
  });

  it("carries id, title and action of the alert", () => {
    const vm = bannerVm(stateWith([makeAlert("o2_low", "warning", { title: "O2 LOW", action: "Switch to secondary" })]), "live");
    expect(vm.rows[0]).toMatchObject({ id: "o2_low", title: "O2 LOW", action: "Switch to secondary" });
  });

  it("shows 5 alerts as the first 3 and +2 MORE", () => {
    const vm = bannerVm(stateWith(ids(5)), "live");
    expect(vm.rows.map((r) => r.id)).toEqual(["a1", "a2", "a3"]);
    expect(vm.more).toBe(2);
    expect(vm.moreText).toBe("+2 MORE");
  });

  it("shows 4 alerts as 3 rows and +1 MORE", () => {
    const vm = bannerVm(stateWith(ids(4)), "live");
    expect(vm.rows).toHaveLength(3);
    expect(vm.moreText).toBe("+1 MORE");
  });

  it("counts a large number of alerts", () => {
    const vm = bannerVm(stateWith(ids(10_000)), "live");
    expect(vm.rows).toHaveLength(3);
    expect(vm.moreText).toBe("+9997 MORE");
  });

  it("has the id of the top row as topId (decision B), even when it is acknowledged", () => {
    const alerts = [makeAlert("first", "warning", { acked: true }), makeAlert("second", "caution")];
    const vm = bannerVm(stateWith(alerts), "live");
    expect(vm.topId).toBe("first");
    expect(vm.topId).toBe(vm.rows[0]?.id);
  });

  it("passes acked through, and nothing but true counts as acked", () => {
    const alerts = [makeAlert("a", "warning", { acked: true }), makeAlert("b", "warning", { acked: false })];
    const vm = bannerVm(stateWith(alerts), "live");
    expect(vm.rows.map((r) => r.acked)).toEqual([true, false]);
    const odd = loose<Alert>({ ...makeAlert("c"), acked: "yes" });
    expect(bannerVm(stateWith([odd]), "live").rows[0]?.acked).toBe(false);
  });

  it.each<Conn>(["offline", "connecting"])("keeps the rows but draws them stale when conn is %s", (conn) => {
    const vm = bannerVm(stateWith([makeAlert("w", "warning"), makeAlert("c", "caution")]), conn);
    expect(vm.rows.map((r) => r.id)).toEqual(["w", "c"]);
    for (const row of vm.rows) expect(row).toMatchObject({ level: "stale", ...theme.level.stale });
    expect(vm.visible).toBe(true);
    expect(vm.topId).toBe("w");
  });

  it.each(["critical", "info", "", "toString"])("draws an unknown severity (%j) as a warning", (severity) => {
    const odd = loose<Alert>({ ...makeAlert("x"), severity });
    const vm = bannerVm(stateWith([odd]), "live");
    expect(vm.rows[0]).toMatchObject({ level: "warning", ...theme.level.warning });
  });

  it("uses empty text for missing fields instead of throwing", () => {
    const odd = loose<Alert>({ severity: "warning" });
    const vm = bannerVm(stateWith([odd]), "live");
    expect(vm.rows[0]).toMatchObject({ id: "", title: "", action: "", acked: false });
    expect(vm.topId).toBeNull();
    expect(vm.visible).toBe(true);
  });

  it("keeps special characters in titles", () => {
    const vm = bannerVm(stateWith([makeAlert("u", "warning", { title: "O₂ — ⚠ \u{1F680} ' \" <b>" })]), "live");
    expect(vm.rows[0]?.title).toBe("O₂ — ⚠ \u{1F680} ' \" <b>");
  });

  it("does not change its input", () => {
    const state = deepFreeze(stateWith(ids(5)));
    expect(() => bannerVm(state, "live")).not.toThrow();
  });
});

describe("bannerVm, acknowledged rows", () => {
  it("says ACK and dims the action once acknowledged, and nothing before", () => {
    const vm = bannerVm(stateWith([makeAlert("seen", "warning", { acked: true }), makeAlert("new", "warning")]), "live");
    expect(vm.rows[0]).toMatchObject({ ackText: "ACK", actionColor: theme.color.label });
    expect(vm.rows[1]).toMatchObject({ ackText: "", actionColor: theme.color.text });
  });
});

