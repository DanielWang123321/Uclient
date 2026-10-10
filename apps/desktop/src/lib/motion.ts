// Motion control bar settings and pure helpers (simulation only).
// All tunables live here; a settings page will make them configurable later.

export const MOTION = {
  /** One click moves this far on a linear TCP axis (mm). */
  stepMm: 1,
  /** One click moves this far on a rotation axis or a joint (deg). */
  stepDeg: 1,
  /** Holding a button longer than this switches to continuous motion (ms). */
  longPressMs: 300,
  /** Linear speed at 100 % (mm/s). */
  maxLinearMmS: 230,
  /** Joint and TCP rotation speed at 100 % (deg/s). */
  maxAngularDegS: 40,
  /** Default speed slider position (%). */
  defaultSpeedPct: 50,
  /** Continuous-motion update period (ms). */
  tickMs: 40,
} as const

/** xArm-style simulated controller states. */
export const STATE = { moving: 1, ready: 2, stopped: 4 } as const

export type TcpAxis = 'x' | 'y' | 'z' | 'roll' | 'pitch' | 'yaw'
export type JogTarget = { kind: 'joint'; index: number } | { kind: 'tcp'; axis: TcpAxis }

export function isLinear(t: JogTarget): boolean {
  return t.kind === 'tcp' && (t.axis === 'x' || t.axis === 'y' || t.axis === 'z')
}

/** Single-click increment (mm or deg). */
export function stepSize(t: JogTarget): number {
  return isLinear(t) ? MOTION.stepMm : MOTION.stepDeg
}

/** Continuous rate (mm/s or deg/s) at a speed percentage. */
export function rate(t: JogTarget, speedPct: number): number {
  const pct = Math.min(100, Math.max(1, speedPct)) / 100
  return (isLinear(t) ? MOTION.maxLinearMmS : MOTION.maxAngularDegS) * pct
}

/** Move joint i by delta, clamped to [lo, hi]. hitLimit is true when the clamp kicked in. */
export function stepJoint(q: number[], i: number, delta: number, limits: [number, number][]): { q: number[]; hitLimit: boolean } {
  const [lo, hi] = limits[i] ?? [-Infinity, Infinity]
  const want = q[i] + delta
  const next = [...q]
  next[i] = Math.min(hi, Math.max(lo, want))
  return { q: next, hitLimit: want > hi + 1e-9 || want < lo - 1e-9 }
}

/** One interpolation step from q towards target at maxStep deg per joint; done when reached. */
export function approach(q: number[], target: number[], maxStep: number): { q: number[]; done: boolean } {
  const diff = target.map((t, i) => t - q[i])
  const far = Math.max(0, ...diff.map(Math.abs))
  if (far <= maxStep) return { q: [...target], done: true }
  const k = maxStep / far // move all joints proportionally so they arrive together
  return { q: q.map((v, i) => v + diff[i] * k), done: false }
}

/**
 * Click vs. press-and-hold detector. Short press -> onClick on release;
 * press longer than longPressMs -> onHoldStart, then onHoldEnd on release.
 */
export class PressHold {
  private timer: ReturnType<typeof setTimeout> | null = null
  private holding = false
  private down = false
  constructor(
    private cb: { onClick: () => void; onHoldStart: () => void; onHoldEnd: () => void },
    private ms: number = MOTION.longPressMs,
  ) {}
  press() {
    if (this.down) return
    this.down = true
    this.holding = false
    this.timer = setTimeout(() => {
      this.timer = null
      this.holding = true
      this.cb.onHoldStart()
    }, this.ms)
  }
  release() {
    if (!this.down) return
    this.down = false
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
      this.cb.onClick()
    } else if (this.holding) {
      this.holding = false
      this.cb.onHoldEnd()
    }
  }
  /** Pointer left / cancelled: never counts as a click. */
  cancel() {
    if (!this.down) return
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
      this.down = false
      return
    }
    this.release()
  }
}

/** Which pad segment (0 top, 1 right, 2 bottom, 3 left) a point hits, or -1 for the hub / outside. */
export function padSegment(dx: number, dy: number, inner: number, outer: number): number {
  const r = Math.hypot(dx, dy)
  if (r < inner || r > outer) return -1
  const a = (Math.atan2(dx, -dy) * 180) / Math.PI // 0 = up, clockwise
  return Math.round(((a + 360) % 360) / 90) % 4
}
