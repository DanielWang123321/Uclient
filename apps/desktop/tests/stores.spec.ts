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
  default_q_deg: [0, 0, 0, 0, 0, 0],
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
      'robot.load': () => LOAD,
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
})
