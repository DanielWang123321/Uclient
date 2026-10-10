import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useEngineStore } from '../src/stores/engine'
import { useRobotStore } from '../src/stores/robot'
import { FakeWs, HELLO } from './fakeEngine'
import { RpcClient } from '../src/rpc/client'

const LOAD = {
  key: 'uf850', robot_name: 'uf850', dof: 6, session_id: 's1',
  joint_names: ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6'],
  effort_limits_nm: [200, 200, 90, 68, 19, 19], visual_urdf_relpath: 'urdf/uf850/uf850_visual.glb.urdf',
  home_q_deg: [0, 0, 0, 0, 0, 0], end_effectors: ['none'], limits_deg: Array(6).fill([-360, 360]),
  default_q_deg: [0, 0, 0, 0, 0, 0], end_effector: 'none', default_tcp_offset: [0, 0, 0, 0, 0, 0], default_tcp_source: 'none',
}
const EE_TCP: Record<string, number[]> = {
  none: [0, 0, 0, 0, 0, 0],
  gripper_g2: [0, 0, 172, 0, 0, 0],
  bio_gripper_g2: [159.5, 0, 59.5, 0, 0, 0],
}
const GOLDEN_Q = [0, -86.401, -144.409, -180, 58.007, -180]
const TORQUE = {
  tau_nm: [0, 74.958, -30.634, -0.662, 0, 0], effort_limits_nm: LOAD.effort_limits_nm,
  utilization: [0, 0.375, 0.34, 0.0097, 0, 0], over_limit: Array(6).fill(false),
}

describe('robot store', () => {
  let ws: FakeWs
  beforeEach(async () => {
    setActivePinia(createPinia())
    const handlers = {
      'system.hello': () => HELLO,
      'robot.list': () => [{ key: 'uf850', robot_name: 'uf850', dof: 6, end_effectors: ['none'] }],
      'robot.load': (p: Record<string, unknown>) => {
        const ee = String(p.end_effector ?? 'none')
        if (!(ee in EE_TCP)) throw { code: -32602, message: `end effector ${ee} not available` }
        return { ...LOAD, end_effector: ee, default_tcp_offset: EE_TCP[ee], end_effectors: Object.keys(EE_TCP),
          visual_urdf_relpath: ee === 'none' ? LOAD.visual_urdf_relpath : `urdf/uf850/uf850_${ee}.urdf` }
      },
      'tcp.set': () => ({ ok: true }),
      'payload.set': () => ({ ok: true }),
      'kin.fk': () => ({ tcp_pose: [830, 0, 200, -180, 0, 0], flange_pose: [830, 0, 200, -180, 0, 0] }),
      'dyn.gravity': () => TORQUE,
      'check.pose': () => ({
        recommended: 0, reachable: true,
        solutions: [{ q_deg: GOLDEN_Q, branch: { elbow: 'up', wrist: 'noflip' }, err_mm: 0, err_deg: 0, limit_margin_deg: 1, ...TORQUE }],
      }),
    }
    const engine = useEngineStore()
    const ok = await engine.connect(
      async () => ({ port: 1, token: 't' }),
      () => new RpcClient(() => (ws = new FakeWs(handlers))),
    )
    expect(ok).toBe(true)
    expect(engine.hello?.pinocchio_version).toBe('4.0.0')
  })

  it('loads a robot, applies payload and checks the U1 pose', async () => {
    const robot = useRobotStore()
    await robot.fetchRobots()
    await robot.load('uf850')
    expect(robot.sessionId).toBe('s1')
    await robot.applyPayload({ mass_kg: 3, com_mm: [0, 0, 35] })
    expect(ws.sent.find((m) => m.method === 'payload.set' && m.params.mass_kg === 3)?.params.com_mm).toEqual([0, 0, 35])
    await robot.checkPose([830, 0, 200, -180, 0, 0])
    expect(robot.q).toEqual(GOLDEN_Q)
    expect(robot.torque?.tau_nm[1]).toBeCloseTo(74.958, 3)
    expect(ws.sent.find((m) => m.method === 'check.pose')?.params.frame).toBe('tcp')
  })

  it('mounting a gripper sets its default TCP but keeps the payload (tool is visual only)', async () => {
    const robot = useRobotStore()
    await robot.load('uf850')
    await robot.applyPayload({ mass_kg: 3, com_mm: [0, 0, 35] })
    await robot.setQ([0, -86.401, -144.409, -180, 58.007, -180])
    expect(await robot.select('uf850', 'gripper_g2')).toBe(true)
    expect(robot.endEffector).toBe('gripper_g2')
    expect(robot.tcpOffset).toEqual([0, 0, 172, 0, 0, 0])
    expect(robot.payload).toEqual({ mass_kg: 3, com_mm: [0, 0, 35] })
    expect(robot.q[1]).toBeCloseTo(-86.401) // same arm: pose kept
    const tcpCall = ws.sent.filter((m) => m.method === 'tcp.set').pop()
    expect(tcpCall?.params.offset).toEqual([0, 0, 172, 0, 0, 0])
    const plCall = ws.sent.filter((m) => m.method === 'payload.set').pop()
    expect(plCall?.params).toMatchObject({ mass_kg: 3, com_mm: [0, 0, 35] })

    await robot.select('uf850', 'bio_gripper_g2')
    expect(robot.tcpOffset).toEqual([159.5, 0, 59.5, 0, 0, 0])
    await robot.select('uf850', 'none')
    expect(robot.tcpOffset).toEqual([0, 0, 0, 0, 0, 0])
  })

  it('keeps a user-edited TCP while the tool is unchanged and reports load errors', async () => {
    const robot = useRobotStore()
    await robot.select('uf850', 'gripper_g2')
    await robot.applyTcp([0, 0, 120, 0, 0, 0])
    await robot.applyPayload({ mass_kg: 1, com_mm: [0, 0, 10] })
    expect(robot.tcpOffset).toEqual([0, 0, 120, 0, 0, 0])
    expect(await robot.select('uf850', 'nope')).toBe(false)
    expect(robot.lastError).toMatch(/not available/)
    expect(robot.endEffector).toBe('gripper_g2')
    expect(robot.tcpOffset).toEqual([0, 0, 120, 0, 0, 0])
  })
})
