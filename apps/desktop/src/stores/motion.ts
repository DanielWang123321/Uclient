// Simulated motion control (no real robot): click = one step, hold = continuous, release/STOP = state 4.
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useEngineStore } from './engine'
import { useRobotStore } from './robot'
import { i18n } from '../i18n'
import { RpcError } from '../rpc/client'
import type { JogResult } from '../rpc/types'
import { MOTION, STATE, approach, rate, stepJoint, stepSize, type JogTarget } from '../lib/motion'

const IK_UNREACHABLE = 3001
const IK_NOT_CONVERGED = 3002
const JOINT_LIMIT = 3003

const MAX_DT_S = 0.5

class MotionError extends Error {}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))
const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now())

export const useMotionStore = defineStore('motion', () => {
  const engine = useEngineStore()
  const robot = useRobotStore()
  const speed = ref<number>(MOTION.defaultSpeedPct)
  const state = ref<number>(STATE.ready)
  const active = ref<JogTarget | null>(null)
  let token = 0

  function limits(): [number, number][] {
    return robot.info?.limits_deg ?? robot.q.map(() => [-360, 360] as [number, number])
  }

  function describe(e: unknown): string {
    const t = i18n.global.t
    if (e instanceof MotionError) return e.message
    if (e instanceof RpcError) {
      if (e.code === JOINT_LIMIT) return t('motion.errLimit')
      if (e.code === IK_UNREACHABLE || e.code === IK_NOT_CONVERGED) return t('motion.errUnreachable')
    }
    return e instanceof Error ? e.message : String(e)
  }

  /** Apply one increment (mm or deg, signed). Throws MotionError/RpcError when the move is impossible. */
  async function applyDelta(t: JogTarget, delta: number) {
    if (t.kind === 'joint') {
      const r = stepJoint(robot.q, t.index, delta, limits())
      void robot.setQ(r.q)
      if (r.hitLimit) throw new MotionError(i18n.global.t('motion.errJointLimit', { j: t.index + 1 }))
      return
    }
    const r = await engine.call<JogResult>('motion.jog_tcp', {
      session_id: robot.sessionId, q_deg: [...robot.q], axis: t.axis, delta,
    })
    void robot.setQ(r.q_deg)
  }

  async function fail(e: unknown) {
    stop()
    try {
      await ElMessageBox.alert(describe(e), i18n.global.t('motion.errTitle'), { type: 'warning' })
    } catch {
      /* dialog closed */
    }
  }

  /** Single click: one step (1 mm / 1 deg). */
  async function step(t: JogTarget, dir: 1 | -1) {
    if (!robot.sessionId) return
    const my = ++token
    state.value = STATE.moving
    active.value = t
    try {
      await applyDelta(t, dir * stepSize(t))
      if (my === token) stop()
    } catch (e) {
      await fail(e)
    }
  }

  /** Press-and-hold: move continuously until stop(). */
  async function startContinuous(t: JogTarget, dir: 1 | -1) {
    if (!robot.sessionId) return
    const my = ++token
    state.value = STATE.moving
    active.value = t
    let last = now()
    while (my === token) {
      await sleep(MOTION.tickMs)
      if (my !== token) break
      const tNow = now()
      const dt = Math.min(MAX_DT_S, (tNow - last) / 1000) // cap so a stalled tick never jumps far
      last = tNow
      try {
        await applyDelta(t, dir * rate(t, speed.value) * dt)
      } catch (e) {
        if (my === token) await fail(e)
        return
      }
    }
  }

  /** Interpolate all joints to a target at the joint speed (Home / Align). */
  async function moveTo(target: number[]) {
    const my = ++token
    state.value = STATE.moving
    active.value = null
    let last = now()
    while (my === token) {
      await sleep(MOTION.tickMs)
      if (my !== token) return
      const tNow = now()
      const dt = Math.min(MAX_DT_S, (tNow - last) / 1000)
      last = tNow
      const r = approach(robot.q, target, MOTION.maxAngularDegS * (speed.value / 100) * dt)
      void robot.setQ(r.q)
      if (r.done) {
        if (my === token) stop()
        return
      }
    }
  }

  async function home() {
    if (!robot.sessionId) return
    await moveTo(robot.q.map(() => 0))
  }

  async function align() {
    if (!robot.sessionId) return
    try {
      const r = await engine.call<JogResult>('motion.align', { session_id: robot.sessionId, q_deg: [...robot.q] })
      await moveTo(r.q_deg)
    } catch (e) {
      await fail(e instanceof RpcError && e.code === IK_UNREACHABLE ? new MotionError(i18n.global.t('motion.errAlign')) : e)
    }
  }

  /** Release / STOP: cancel any motion and enter state 4. */
  function stop() {
    token++
    active.value = null
    state.value = STATE.stopped
  }

  return { speed, state, active, step, startContinuous, home, align, stop, moveTo }
})
