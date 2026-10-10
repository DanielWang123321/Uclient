import { describe, expect, it } from 'vitest'
import en from '../src/i18n/en.json'
import zh from '../src/i18n/zh.json'

describe('end-effector labels', () => {
  it('exist for every end effector the sidecar can report', () => {
    for (const ee of ['none', 'gripper_g2', 'bio_gripper_g2', 'lite6_gripper', 'lite6_vacuum_gripper']) {
      expect(en.ee[ee as keyof typeof en.ee]).toBeTruthy()
      expect(zh.ee[ee as keyof typeof zh.ee]).toBeTruthy()
    }
  })
})

import { migrate, newProject } from '../src/project/migrate'
describe('stale G2 preset', () => {
  it('drops the v0.1.0 101.1 mm G2 preset (not a TCP)', () => {
    const old = { ...newProject(), tcp_presets: [...newProject().tcp_presets, { id: 'g2', name: 'Gripper G2', offset: [0, 0, 101.1, 0, 0, 0] }], active: { tcp: 'g2', payload: 'p3kg' } }
    const p = migrate(old)
    expect(p.tcp_presets.map((t) => t.id)).toEqual(['flange'])
    expect(p.active.tcp).toBe('flange')
    expect(JSON.stringify(newProject())).not.toContain('101.1')
  })
})
