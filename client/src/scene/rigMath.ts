// The arithmetic of the head-following rig, kept apart from three.js so it can be unit tested.
// Angles are radians about the up axis: 0 looks down -Z, positive turns left.

/** Bring an angle into (-PI, PI]. */
export function wrapAngle(angle: number): number {
  const turn = 2 * Math.PI;
  const wrapped = ((((angle + Math.PI) % turn) + turn) % turn) - Math.PI;
  return wrapped === -Math.PI ? Math.PI : wrapped;
}

/**
 * The yaw of a view direction. Looking straight up or down has no yaw, so `fallback`
 * (the last good value) is returned: the rig only turns, it never tilts or flips.
 */
export function headYaw(dirX: number, dirZ: number, fallback: number): number {
  if (Math.hypot(dirX, dirZ) < 0.001) return fallback;
  return Math.atan2(-dirX, -dirZ);
}

/**
 * Move `current` toward `target` the short way round. `followS` is the time constant:
 * after that long about 63% of the gap is closed, whatever the frame rate.
 */
export function followYaw(current: number, target: number, dtS: number, followS: number): number {
  if (!(dtS > 0)) return wrapAngle(current);
  const gap = wrapAngle(target - current);
  const fraction = followS > 0 ? 1 - Math.exp(-dtS / followS) : 1;
  return wrapAngle(current + gap * fraction);
}
