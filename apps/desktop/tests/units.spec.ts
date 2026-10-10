import { describe, expect, it } from 'vitest'
import { fmt, fmtPct, utilLevel } from '../src/lib/units'
import { torqueCsv } from '../src/lib/csv'

describe('units', () => {
  it('formats numbers and avoids negative zero', () => {
    expect(fmt(74.95812)).toBe('74.958')
    expect(fmt(-0.0001)).toBe('0.000')
    expect(fmt(undefined)).toBe('—')
    expect(fmtPct(0.37479)).toBe('37.5%')
  })
  it('classifies utilisation bands', () => {
    expect(utilLevel(0.2)).toBe('ok')
    expect(utilLevel(-0.6)).toBe('warn')
    expect(utilLevel(0.85)).toBe('high')
    expect(utilLevel(1.2)).toBe('over')
  })
  it('exports torque CSV', () => {
    const csv = torqueCsv(['joint1', 'joint2'], [0, -86.401], {
      tau_nm: [0, 74.958],
      tau_arm_nm: [0, 50.531],
      tau_payload_nm: [0, 24.427],
      effort_limits_nm: [200, 200],
      utilization: [0, 0.37479],
      over_limit: [false, false],
    })
    const lines = csv.trim().split('\n')
    expect(lines[0]).toBe('joint,q_deg,tau_nm,tau_arm_nm,tau_payload_nm,rated_nm,utilization_pct')
    expect(lines[2]).toBe('joint2,-86.4010,74.9580,50.5310,24.4270,200.00,37.48')
  })
})
