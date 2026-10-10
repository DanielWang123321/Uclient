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

describe('legacy Uclient project files', () => {
  it('load unchanged after the UGClient rename', async () => {
    const { migrate, isProjectFileName } = await import('../src/project/migrate')
    const legacy = {
      schema_version: 1,
      app: { name: 'Uclient', version: '0.1.0' },
      core: { ufactory_genesis_commit: '60fe926', pinocchio: '4.0.0' },
      robot: { key: 'xarm6_1305', end_effector: 'gripper_g2', calibration: null, mounting: { gravity_dir: [0, 0, -1] } },
      tcp_presets: [{ id: 'flange', name: 'Flange', offset: [0, 0, 0, 0, 0, 0] }],
      payload_presets: [{ id: 'p1', name: 'box', mass_kg: 1, com_mm: [0, 0, 20], inertia_kgm2: null }],
      active: { tcp: 'flange', payload: 'p1' },
      poses: [{ id: 'a', name: 'a', tcp_pose: [400, 0, 300, 180, 0, 0] }],
      trajectories: [],
      results: [],
    }
    const p = migrate(JSON.parse(JSON.stringify(legacy)))
    expect(p.robot.key).toBe('xarm6_1305')
    expect(p.robot.end_effector).toBe('gripper_g2')
    expect(p.payload_presets[0].mass_kg).toBe(1)
    expect(p.app.name).toBe('Uclient')
    expect(isProjectFileName('850_check.uclient.json')).toBe(true)
    expect(isProjectFileName('850_check.ugclient.json')).toBe(true)
    expect(isProjectFileName('notes.json')).toBe(false)
  })
})
