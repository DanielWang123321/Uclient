// User safety boundary (Settings > Safety), stored per robot model. Pure helpers.

/** TCP bounds are [x, y, z] in mm (base frame), null = unbounded. Joint bounds in deg. */
export interface Boundary {
  tcpMin: (number | null)[]
  tcpMax: (number | null)[]
  jointMin: number[]
  jointMax: number[]
}

export type Violation =
  | { kind: 'joint'; index: number; side: 'min' | 'max'; limit: number }
  | { kind: 'tcp'; axis: 0 | 1 | 2; side: 'min' | 'max'; limit: number }

export function defaultBoundary(model: [number, number][]): Boundary {
  return { tcpMin: [null, null, null], tcpMax: [null, null, null], jointMin: model.map((l) => l[0]), jointMax: model.map((l) => l[1]) }
}

/** Fill gaps and clamp the user joint bounds inside the model limits (min <= max). */
export function normalizeBoundary(b: Partial<Boundary> | undefined, model: [number, number][]): Boundary {
  const d = defaultBoundary(model)
  const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)
  const out: Boundary = {
    tcpMin: [0, 1, 2].map((i) => num(b?.tcpMin?.[i])),
    tcpMax: [0, 1, 2].map((i) => num(b?.tcpMax?.[i])),
    jointMin: model.map(([lo, hi], i) => Math.min(hi, Math.max(lo, num(b?.jointMin?.[i]) ?? d.jointMin[i]))),
    jointMax: model.map(([lo, hi], i) => Math.min(hi, Math.max(lo, num(b?.jointMax?.[i]) ?? d.jointMax[i]))),
  }
  out.jointMax = out.jointMax.map((v, i) => Math.max(v, out.jointMin[i]))
  for (let i = 0; i < 3; i++) {
    const lo = out.tcpMin[i]
    const hi = out.tcpMax[i]
    if (lo !== null && hi !== null && hi < lo) out.tcpMax[i] = lo
  }
  return out
}

export function jointLimits(b: Boundary): [number, number][] {
  return b.jointMin.map((lo, i) => [lo, b.jointMax[i]])
}

export function hasTcpBounds(b: Boundary): boolean {
  return [...b.tcpMin, ...b.tcpMax].some((v) => v !== null)
}

const EPS = 1e-9

/**
 * First boundary violated by moving prev -> next. A value already outside the boundary may still
 * move back towards it (only moves that go further out are blocked).
 */
export function checkBoundary(
  b: Boundary,
  prevQ: number[],
  nextQ: number[],
  prevTcp?: number[] | null,
  nextTcp?: number[] | null,
): Violation | null {
  for (let i = 0; i < nextQ.length; i++) {
    const n = nextQ[i]
    const p = prevQ[i] ?? n
    if (n < b.jointMin[i] - EPS && n < p - EPS) return { kind: 'joint', index: i, side: 'min', limit: b.jointMin[i] }
    if (n > b.jointMax[i] + EPS && n > p + EPS) return { kind: 'joint', index: i, side: 'max', limit: b.jointMax[i] }
  }
  if (nextTcp) {
    for (const a of [0, 1, 2] as const) {
      const n = nextTcp[a]
      const p = prevTcp?.[a] ?? n
      const lo = b.tcpMin[a]
      const hi = b.tcpMax[a]
      if (lo !== null && n < lo - EPS && n < p - EPS) return { kind: 'tcp', axis: a, side: 'min', limit: lo }
      if (hi !== null && n > hi + EPS && n > p + EPS) return { kind: 'tcp', axis: a, side: 'max', limit: hi }
    }
  }
  return null
}

export function violationAxis(v: Violation): string {
  return v.kind === 'joint' ? `J${v.index + 1}` : `TCP ${'XYZ'[v.axis]}`
}
