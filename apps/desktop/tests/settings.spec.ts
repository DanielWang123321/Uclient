import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { alert } = vi.hoisted(() => ({ alert: vi.fn<(...args: unknown[]) => Promise<string>>(async () => 'confirm') }))
vi.mock('element-plus', () => ({ ElMessageBox: { alert } }))

import { useEngineStore } from '../src/stores/engine'
import { useRobotStore } from '../src/stores/robot'
import { useMotionStore } from '../src/stores/motion'
import { SETTINGS_KEY, useSettingsStore } from '../src/stores/settings'
import { RpcClient } from '../src/rpc/client'
import { FakeWs, HELLO } from './fakeEngine'
import { MOTION, STATE, sanitizeStep } from '../src/lib/motion'
import { checkBoundary, defaultBoundary, normalizeBoundary } from '../src/lib/boundary'

const MODEL: [number, number][] = [[-360, 360], [-150, 150], [-3.5, 300], [-360, 360], [-124, 124], [-360, 360]]
const LOAD = {
  key: 'uf850', robot_name: 'uf850', dof: 6, session_id: 's1',
  joint_names: ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6'],
  effort_limits_nm: [1, 1, 1, 1, 1, 1], visual_urdf_relpath: 'x.urdf', home_q_deg: [0, 0, 0, 0, 0, 0],
  end_effectors: ['none'], limits_deg: MODEL,
  default_q_deg: [0, 0, 0, 0, 0, 0], end_effector: 'none', default_tcp_offset: [0, 0, 0, 0, 0, 0], default_tcp_source: 'none',
}
// Fake kinematics: TCP z = 200 + J2 (mm); a TCP jog moves J1 by delta and z by delta.
const tcpOf = (q: number[]) => [0, 0, 200 + q[1], 180, 0, 0]

describe('boundary helpers', () => {
  it('defaults to model joint limits and unbounded TCP, clamps user joint bounds inside the model', () => {
    expect(defaultBoundary(MODEL).tcpMax).toEqual([null, null, null])
    const b = normalizeBoundary({ jointMin: [-400, -10], jointMax: [400, 5] }, MODEL)
    expect(b.jointMin.slice(0, 2)).toEqual([-360, -10])
    expect(b.jointMax.slice(0, 2)).toEqual([360, 5])
    expect(b.jointMin[4]).toBe(-124)
  })
  it('blocks only moves that go further outside', () => {
    const b = normalizeBoundary({ jointMax: [360, 10], tcpMin: [null, null, 100] }, MODEL)
    expect(checkBoundary(b, [0, 9, 0, 0, 0, 0], [0, 11, 0, 0, 0, 0])).toMatchObject({ kind: 'joint', index: 1, side: 'max', limit: 10 })
    expect(checkBoundary(b, [0, 20, 0, 0, 0, 0], [0, 19, 0, 0, 0, 0])).toBeNull() // moving back in is allowed
    expect(checkBoundary(b, [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 101], [0, 0, 99])).toMatchObject({ kind: 'tcp', axis: 2, side: 'min' })
  })
  it('validates click steps', () => {
    expect(sanitizeStep(5, MOTION.stepMmRange, 1)).toBe(5)
    expect(sanitizeStep(-1, MOTION.stepMmRange, 1)).toBe(1)
    expect(sanitizeStep('abc', MOTION.stepMmRange, 1)).toBe(1)
    expect(sanitizeStep(1000, MOTION.stepMmRange, 1)).toBe(100)
    expect(sanitizeStep(90, MOTION.stepDegRange, 1)).toBe(45)
  })
})

describe('settings + motion', () => {
  let ws: FakeWs
  beforeEach(async () => {
    localStorage.clear()
    alert.mockClear()
    setActivePinia(createPinia())
    const handlers = {
      'system.hello': () => HELLO,
      'robot.load': () => LOAD,
      'tcp.set': () => ({ ok: true }),
      'payload.set': () => ({ ok: true }),
      'kin.fk': (p: Record<string, unknown>) => ({ tcp_pose: tcpOf(p.q_deg as number[]), flange_pose: tcpOf(p.q_deg as number[]) }),
      'dyn.gravity': () => ({ tau_nm: [0, 0, 0, 0, 0, 0], effort_limits_nm: [1, 1, 1, 1, 1, 1], utilization: [0, 0, 0, 0, 0, 0], over_limit: [] }),
      'motion.jog_tcp': (p: Record<string, unknown>) => {
        const q = [...(p.q_deg as number[])]
        q[0] += Number(p.delta)
        const tcp = tcpOf(p.q_deg as number[])
        tcp[2] += Number(p.delta)
        return { q_deg: q, tcp_pose: tcp }
      },
      'motion.align': () => ({ q_deg: [0, 50, 0, 0, 0, 0], tcp_pose: tcpOf([0, 50, 0, 0, 0, 0]) }),
    }
    await useEngineStore().connect(async () => ({ port: 1, token: 't' }), () => new RpcClient(() => (ws = new FakeWs(handlers))))
    await useRobotStore().load('uf850')
  })

  it('click steps come from the settings', async () => {
    const s = useSettingsStore()
    const m = useMotionStore()
    const robot = useRobotStore()
    s.setStepMm(5)
    s.setStepDeg(2.5)
    await m.step({ kind: 'tcp', axis: 'z' }, 1)
    expect(ws.sent.find((c) => c.method === 'motion.jog_tcp')?.params.delta).toBe(5)
    await m.step({ kind: 'joint', index: 3 }, -1)
    expect(robot.q[3]).toBe(-2.5)
    await robot.setQ([10, 0, 0, 0, 0, 0])
    await m.goStep('home')
    expect(robot.q[0]).toBeCloseTo(7.5)
  })

  it('persists settings and keeps boundaries per robot model', () => {
    const s = useSettingsStore()
    s.setStepMm(3)
    s.setBoundary('uf850', normalizeBoundary({ jointMax: [360, 20] }, MODEL), MODEL)
    s.save()
    setActivePinia(createPinia())
    const s2 = useSettingsStore()
    expect(s2.stepMm).toBe(3)
    expect(s2.boundaryFor('uf850', MODEL).jointMax[1]).toBe(20)
    expect(s2.boundaryFor('lite6', MODEL).jointMax[1]).toBe(150)
    expect(JSON.parse(localStorage.getItem(SETTINGS_KEY)!).boundaries.uf850).toBeTruthy()
  })

  it('a joint jog stops on the user boundary and names the joint', async () => {
    const s = useSettingsStore()
    const m = useMotionStore()
    const robot = useRobotStore()
    s.setBoundary('uf850', normalizeBoundary({ jointMax: [360, 10] }, MODEL), MODEL)
    await robot.setQ([0, 9.5, 0, 0, 0, 0])
    await m.step({ kind: 'joint', index: 1 }, 1)
    expect(robot.q[1]).toBe(10)
    expect(m.state).toBe(STATE.stopped)
    expect(alert).toHaveBeenCalledTimes(1)
    expect(String(alert.mock.calls[0][0])).toMatch(/J2/)
  })

  it('a TCP jog that leaves the TCP box is refused and names the axis', async () => {
    const s = useSettingsStore()
    const m = useMotionStore()
    const robot = useRobotStore()
    s.setBoundary('uf850', normalizeBoundary({ tcpMax: [null, null, 200.5] }, MODEL), MODEL)
    await m.step({ kind: 'tcp', axis: 'z' }, 1)
    expect(robot.q).toEqual([0, 0, 0, 0, 0, 0])
    expect(String(alert.mock.calls[0][0])).toMatch(/TCP Z/)
  })

  it('Home and Align stop at the boundary', async () => {
    const s = useSettingsStore()
    const m = useMotionStore()
    const robot = useRobotStore()
    m.speed = 100
    // Align target needs J2 = 50 but the TCP z is capped at 230 mm (J2 <= 30 in the fake kinematics)
    s.setBoundary('uf850', normalizeBoundary({ tcpMax: [null, null, 230] }, MODEL), MODEL)
    await m.goStart('align')
    expect(robot.q[1]).toBeLessThanOrEqual(30)
    expect(robot.q[1]).toBeGreaterThan(20)
    expect(m.state).toBe(STATE.stopped)
    expect(String(alert.mock.calls[0][0])).toMatch(/TCP Z/)
    // Home blocked by a joint boundary that excludes 0
    alert.mockClear()
    s.setBoundary('uf850', normalizeBoundary({ jointMin: [-360, 20] }, MODEL), MODEL)
    await robot.setQ([0, 25, 0, 0, 0, 0])
    await m.goStart('home')
    expect(robot.q[1]).toBeGreaterThanOrEqual(20)
    expect(String(alert.mock.calls[0][0])).toMatch(/J2/)
  })
})
