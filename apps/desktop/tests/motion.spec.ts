import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { alert } = vi.hoisted(() => ({ alert: vi.fn(async () => 'confirm') }))
vi.mock('element-plus', () => ({ ElMessageBox: { alert } }))

import { useEngineStore } from '../src/stores/engine'
import { useRobotStore } from '../src/stores/robot'
import { useMotionStore } from '../src/stores/motion'
import { RpcClient } from '../src/rpc/client'
import { FakeWs, HELLO } from './fakeEngine'
import { MOTION, PressHold, STATE, approach, padSegment, rate, stepJoint, stepSize } from '../src/lib/motion'

describe('motion helpers', () => {
  it('uses 1 mm / 1 deg steps and the 230 mm/s, 40 deg/s speed scale', () => {
    expect(stepSize({ kind: 'tcp', axis: 'x' })).toBe(1)
    expect(stepSize({ kind: 'tcp', axis: 'yaw' })).toBe(1)
    expect(stepSize({ kind: 'joint', index: 2 })).toBe(1)
    expect(rate({ kind: 'tcp', axis: 'z' }, 100)).toBe(230)
    expect(rate({ kind: 'tcp', axis: 'z' }, 50)).toBe(115)
    expect(rate({ kind: 'tcp', axis: 'roll' }, 50)).toBe(20)
    expect(rate({ kind: 'joint', index: 0 }, 100)).toBe(40)
    expect(MOTION.longPressMs).toBe(300)
  })
  it('clamps joints at their limits and reports it', () => {
    expect(stepJoint([0, 149.5], 1, 1, [[-360, 360], [-150, 150]])).toEqual({ q: [0, 150], hitLimit: true })
    expect(stepJoint([0, 10], 1, -1, [[-360, 360], [-150, 150]])).toEqual({ q: [0, 9], hitLimit: false })
  })
  it('interpolates all joints together', () => {
    const r = approach([0, 0], [10, -5], 2)
    expect(r.done).toBe(false)
    expect(r.q[0]).toBeCloseTo(2)
    expect(r.q[1]).toBeCloseTo(-1)
    expect(approach([9, -4.5], [10, -5], 2)).toEqual({ q: [10, -5], done: true })
  })
  it('maps pad hits to segments (0 top, 1 right, 2 bottom, 3 left)', () => {
    expect(padSegment(0, -70, 47, 90)).toBe(0)
    expect(padSegment(70, 0, 47, 90)).toBe(1)
    expect(padSegment(0, 70, 47, 90)).toBe(2)
    expect(padSegment(-70, 0, 47, 90)).toBe(3)
    expect(padSegment(10, 10, 47, 90)).toBe(-1)
  })
  it('tells click from press-and-hold', () => {
    vi.useFakeTimers()
    const cb = { onClick: vi.fn(), onHoldStart: vi.fn(), onHoldEnd: vi.fn() }
    const h = new PressHold(cb, 300)
    h.press()
    vi.advanceTimersByTime(100)
    h.release()
    expect(cb.onClick).toHaveBeenCalledTimes(1)
    h.press()
    vi.advanceTimersByTime(301)
    expect(cb.onHoldStart).toHaveBeenCalledTimes(1)
    h.release()
    expect(cb.onHoldEnd).toHaveBeenCalledTimes(1)
    expect(cb.onClick).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })
})

const LOAD = {
  key: 'uf850', robot_name: 'uf850', dof: 6, session_id: 's1',
  joint_names: ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6'],
  effort_limits_nm: [1, 1, 1, 1, 1, 1], visual_urdf_relpath: 'x.urdf', home_q_deg: [0, 0, 0, 0, 0, 0],
  end_effectors: ['none'], limits_deg: [[-360, 360], [-150, 150], [-3.5, 300], [-360, 360], [-124, 124], [-360, 360]],
  default_q_deg: [0, 0, 0, 0, 0, 0], end_effector: 'none', default_tcp_offset: [0, 0, 0, 0, 0, 0], default_tcp_source: 'none',
}

describe('motion store (simulation)', () => {
  let ws: FakeWs
  let unreachable = false
  beforeEach(async () => {
    alert.mockClear()
    unreachable = false
    setActivePinia(createPinia())
    const handlers = {
      'system.hello': () => HELLO,
      'robot.load': () => LOAD,
      'tcp.set': () => ({ ok: true }),
      'payload.set': () => ({ ok: true }),
      'kin.fk': () => ({ tcp_pose: [0, 0, 0, 0, 0, 0], flange_pose: [0, 0, 0, 0, 0, 0] }),
      'dyn.gravity': () => ({ tau_nm: [0, 0, 0, 0, 0, 0], effort_limits_nm: [1, 1, 1, 1, 1, 1], utilization: [0, 0, 0, 0, 0, 0], over_limit: [] }),
      'motion.jog_tcp': (p: Record<string, unknown>) => {
        if (unreachable) throw { code: 3001, message: 'unreachable' }
        const q = [...(p.q_deg as number[])]
        q[0] += Number(p.delta)
        return { q_deg: q, tcp_pose: [0, 0, 0, 0, 0, 0] }
      },
      'motion.align': () => {
        if (unreachable) throw { code: 3001, message: 'unreachable' }
        return { q_deg: [0, 0, 0, 2, 3, 4], tcp_pose: [0, 0, 0, 180, 0, 0] }
      },
    }
    const engine = useEngineStore()
    await engine.connect(async () => ({ port: 1, token: 't' }), () => new RpcClient(() => (ws = new FakeWs(handlers))))
    await useRobotStore().load('uf850')
  })
  afterEach(() => useMotionStore().stop())

  it('a click moves a joint one degree and ends in state 4', async () => {
    const m = useMotionStore()
    const robot = useRobotStore()
    await m.step({ kind: 'joint', index: 1 }, 1)
    expect(robot.q[1]).toBe(1)
    expect(m.state).toBe(STATE.stopped)
  })

  it('a TCP click calls the sidecar jog in the base frame with 1 mm', async () => {
    const m = useMotionStore()
    await m.step({ kind: 'tcp', axis: 'x' }, -1)
    const call = ws.sent.find((c) => c.method === 'motion.jog_tcp')
    expect(call?.params).toMatchObject({ axis: 'x', delta: -1 })
  })

  it('hitting a joint limit stops and pops up a message', async () => {
    const m = useMotionStore()
    const robot = useRobotStore()
    await robot.setQ([0, 0, -3, 0, 0, 0])
    await m.step({ kind: 'joint', index: 2 }, -1)
    expect(robot.q[2]).toBe(-3.5)
    expect(m.state).toBe(STATE.stopped)
    expect(alert).toHaveBeenCalledTimes(1)
  })

  it('an unreachable TCP move pops up a message', async () => {
    unreachable = true
    await useMotionStore().step({ kind: 'tcp', axis: 'z' }, 1)
    expect(alert).toHaveBeenCalledTimes(1)
  })

  it('continuous motion runs at the slider speed until STOP (state 4)', async () => {
    const m = useMotionStore()
    const robot = useRobotStore()
    m.speed = 100
    const run = m.startContinuous({ kind: 'joint', index: 0 }, 1)
    expect(m.state).toBe(STATE.moving)
    await new Promise((r) => setTimeout(r, 260))
    m.stop()
    await run
    expect(m.state).toBe(STATE.stopped)
    // 40 deg/s for ~0.26 s, allow for timer jitter
    expect(robot.q[0]).toBeGreaterThan(4)
    expect(robot.q[0]).toBeLessThan(14)
  })

  it('Home drives all joints to zero; Align uses the sidecar result', async () => {
    const m = useMotionStore()
    const robot = useRobotStore()
    m.speed = 100
    await robot.setQ([1, 1, 1, 1, 1, 1])
    await m.home()
    expect(robot.q).toEqual([0, 0, 0, 0, 0, 0])
    await m.align()
    expect(robot.q).toEqual([0, 0, 0, 2, 3, 4])
    unreachable = true
    await m.align()
    expect(alert).toHaveBeenCalledTimes(1)
  })
})
