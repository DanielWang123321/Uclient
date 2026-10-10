import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useEngineStore } from './engine'
import type {
  CheckResult,
  FkResult,
  Pose6,
  RobotListItem,
  RobotLoadResult,
  TorqueResult,
} from '../rpc/types'

export const useRobotStore = defineStore('robot', () => {
  const engine = useEngineStore()
  const robots = ref<RobotListItem[]>([])
  const key = ref('uf850')
  const endEffector = ref('none')
  const info = ref<RobotLoadResult | null>(null)
  const q = ref<number[]>([])
  const tcpOffset = ref<number[]>([0, 0, 0, 0, 0, 0])
  const payload = ref({ mass_kg: 0, com_mm: [0, 0, 0] })
  const fk = ref<FkResult | null>(null)
  const torque = ref<TorqueResult | null>(null)
  const check = ref<CheckResult | null>(null)
  const selectedSolution = ref(0)
  const lastError = ref('')
  const busy = ref(false)

  const sessionId = computed(() => info.value?.session_id ?? '')

  async function fetchRobots() {
    robots.value = await engine.call<RobotListItem[]>('robot.list')
  }

  async function load(robotKey = key.value, ee = endEffector.value) {
    const r = await engine.call<RobotLoadResult>('robot.load', { robot: robotKey, end_effector: ee })
    key.value = robotKey
    endEffector.value = ee
    info.value = r
    q.value = [...r.default_q_deg]
    check.value = null
    await applyTcp()
    await applyPayload()
  }

  async function applyTcp(offset = tcpOffset.value) {
    tcpOffset.value = [...offset]
    if (!sessionId.value) return
    await engine.call('tcp.set', { session_id: sessionId.value, offset: tcpOffset.value })
    await refresh()
  }

  async function applyPayload(p = payload.value) {
    payload.value = { mass_kg: p.mass_kg, com_mm: [...p.com_mm] }
    if (!sessionId.value) return
    await engine.call('payload.set', { session_id: sessionId.value, ...payload.value })
    await refresh()
  }

  let pending = false
  let running = false
  /** Recompute FK + gravity torque for the current q (coalesces bursts from slider drags). */
  async function refresh() {
    if (!sessionId.value) return
    if (running) {
      pending = true
      return
    }
    running = true
    try {
      do {
        pending = false
        const params = { session_id: sessionId.value, q_deg: [...q.value] }
        const [f, t] = await Promise.all([
          engine.call<FkResult>('kin.fk', params),
          engine.call<TorqueResult>('dyn.gravity', params),
        ])
        fk.value = f
        torque.value = t
        lastError.value = ''
      } while (pending)
    } catch (e) {
      lastError.value = e instanceof Error ? e.message : String(e)
    } finally {
      running = false
    }
  }

  async function setJoint(i: number, deg: number) {
    q.value[i] = deg
    await refresh()
  }

  async function setQ(next: number[]) {
    q.value = [...next]
    await refresh()
  }

  async function checkPose(target: Pose6, frame: 'tcp' | 'flange' = 'tcp') {
    busy.value = true
    try {
      const r = await engine.call<CheckResult>('check.pose', {
        session_id: sessionId.value,
        target_pose: target,
        frame,
        seed_q_deg: q.value,
      })
      check.value = r
      selectedSolution.value = r.recommended
      await setQ(r.solutions[r.recommended].q_deg)
      lastError.value = ''
    } catch (e) {
      check.value = null
      lastError.value = e instanceof Error ? e.message : String(e)
    } finally {
      busy.value = false
    }
  }

  async function selectSolution(i: number) {
    if (!check.value) return
    selectedSolution.value = i
    await setQ(check.value.solutions[i].q_deg)
  }

  return {
    robots, key, endEffector, info, q, tcpOffset, payload, fk, torque, check, selectedSolution, lastError, busy,
    sessionId, fetchRobots, load, applyTcp, applyPayload, refresh, setJoint, setQ, checkPose, selectSolution,
  }
})
