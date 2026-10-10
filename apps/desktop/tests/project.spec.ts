import { describe, expect, it } from 'vitest'
import { migrate, newProject, SCHEMA_VERSION } from '../src/project/migrate'

describe('project file', () => {
  it('new project matches the golden U1 defaults', () => {
    const p = newProject()
    expect(p.schema_version).toBe(SCHEMA_VERSION)
    expect(p.payload_presets[0]).toMatchObject({ mass_kg: 3, com_mm: [0, 0, 35] })
    expect(p.poses[0].tcp_pose).toEqual([830, 0, 200, -180, 0, 0])
  })
  it('migrates v0 files and keeps user data', () => {
    const p = migrate({ robot: { key: 'lite6', end_effector: 'none', calibration: null, mounting: { gravity_dir: [0, 0, -1] } } })
    expect(p.schema_version).toBe(1)
    expect(p.robot.key).toBe('lite6')
    expect(p.tcp_presets.length).toBeGreaterThan(0)
  })
  it('rejects newer schemas and non-objects', () => {
    expect(() => migrate({ schema_version: 99 })).toThrow(/newer/)
    expect(() => migrate(42)).toThrow()
  })
})
