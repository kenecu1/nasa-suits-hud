import { describe, expect, it } from "vitest";
import { followYaw, headYaw, wrapAngle } from "./rigMath";

const deg = (d: number): number => (d * Math.PI) / 180;

describe("wrapAngle", () => {
  it("leaves zero at zero", () => {
    expect(wrapAngle(0)).toBe(0);
  });

  it("wraps 3PI/2 to -PI/2 and -3PI/2 to PI/2", () => {
    expect(wrapAngle((3 * Math.PI) / 2)).toBeCloseTo(-Math.PI / 2, 9);
    expect(wrapAngle((-3 * Math.PI) / 2)).toBeCloseTo(Math.PI / 2, 9);
  });

  it("always returns a value in (-PI, PI]", () => {
    for (let a = -20; a <= 20; a += 0.37) {
      const wrapped = wrapAngle(a);
      expect(wrapped).toBeGreaterThan(-Math.PI);
      expect(wrapped).toBeLessThanOrEqual(Math.PI);
    }
  });
});

describe("headYaw", () => {
  it("is 0 looking down -Z", () => {
    expect(headYaw(0, -1, 0.5)).toBeCloseTo(0, 9);
  });

  it("is +PI/2 looking down -X (turned left)", () => {
    expect(headYaw(-1, 0, 0.5)).toBeCloseTo(Math.PI / 2, 9);
  });

  it("is -PI/2 looking down +X", () => {
    expect(headYaw(1, 0, 0.5)).toBeCloseTo(-Math.PI / 2, 9);
  });

  it("is PI in absolute value looking down +Z", () => {
    expect(Math.abs(headYaw(0, 1, 0.5))).toBeCloseTo(Math.PI, 9);
  });

  it("returns the fallback when the horizontal part is shorter than 0.001", () => {
    expect(headYaw(0, 0, 1.234)).toBe(1.234);
    expect(headYaw(0.0005, 0.0005, -0.7)).toBe(-0.7);
  });

  it("does not use the fallback when the horizontal part is longer than 0.001", () => {
    expect(headYaw(0, -0.002, 1)).toBeCloseTo(0, 9);
  });
});

describe("followYaw", () => {
  it("leaves the yaw unchanged when dt is 0", () => {
    expect(followYaw(0.3, 1.2, 0, 0.35)).toBeCloseTo(0.3, 12);
  });

  it("closes about 63.2% of the gap when dt equals followS", () => {
    expect(followYaw(0, 1, 0.35, 0.35)).toBeCloseTo(1 - Math.exp(-1), 6);
  });

  it("ends within 0.001 rad of the target for a large dt", () => {
    expect(Math.abs(followYaw(0, 1, 3.5, 0.35) - 1)).toBeLessThan(0.001);
  });

  it("takes the short way round from 170 to -170 degrees", () => {
    const current = deg(170);
    const target = deg(-170);
    const result = followYaw(current, target, 0.1, 0.35);
    expect(Math.abs(wrapAngle(target - result))).toBeLessThan(Math.abs(wrapAngle(target - current)));
    expect(Math.abs(result)).toBeGreaterThan(current);
  });

  it("always returns an angle in (-PI, PI]", () => {
    const pairs: [number, number][] = [
      [deg(170), deg(-170)],
      [deg(-170), deg(170)],
      [deg(179), deg(-179)],
      [0, Math.PI],
      [3, -3],
    ];
    for (const [current, target] of pairs) {
      for (const dt of [0, 0.016, 0.1, 1, 10]) {
        const result = followYaw(current, target, dt, 0.35);
        expect(result).toBeGreaterThan(-Math.PI);
        expect(result).toBeLessThanOrEqual(Math.PI);
      }
    }
  });

  it("is within 1 degree of a target 90 degrees away after 2 s at 60 steps per second", () => {
    const target = deg(90);
    let yaw = 0;
    for (let i = 0; i < 120; i += 1) yaw = followYaw(yaw, target, 1 / 60, 0.35);
    expect(Math.abs(wrapAngle(target - yaw))).toBeLessThan(deg(1));
  });
});
