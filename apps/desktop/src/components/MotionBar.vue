<script setup lang="ts">
// Bottom motion control bar (simulation only). Layout follows the approved v8 mockup.
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRobotStore } from '../stores/robot'
import { useMotionStore } from '../stores/motion'
import { PressHold, padSegment, type JogTarget, type TcpAxis } from '../lib/motion'

const robot = useRobotStore()
const motion = useMotionStore()
const open = ref(true)

const COLORS = ['#f08a24', '#e8475a', '#18c37a', '#3b6ef5', '#8b3cf0', '#e0218a', '#16b5c9']
function lim(i: number): [number, number] {
  return robot.info?.limits_deg[i] ?? [-360, 360]
}
function pct(i: number) {
  const [lo, hi] = lim(i)
  return hi > lo ? ((robot.q[i] - lo) / (hi - lo)) * 100 : 0
}
const fmtLim = (v: number) => String(Math.round(v * 10) / 10)

// One PressHold per button/segment; pointer capture keeps release on the same control.
const holders = new Map<string, PressHold>()
const pressed = ref('')
function holder(id: string, t: JogTarget, dir: 1 | -1) {
  let h = holders.get(id)
  if (!h) {
    h = new PressHold({
      onClick: () => motion.step(t, dir),
      onHoldStart: () => motion.startContinuous(t, dir),
      onHoldEnd: () => motion.stop(),
    })
    holders.set(id, h)
  }
  return h
}
function down(e: PointerEvent, id: string, t: JogTarget, dir: 1 | -1) {
  if (e.button !== 0) return
  ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
  pressed.value = id
  holder(id, t, dir).press()
}
function up(id: string) {
  if (pressed.value === id) pressed.value = ''
  holders.get(id)?.release()
}
function cancel(id: string) {
  if (pressed.value === id) pressed.value = ''
  holders.get(id)?.cancel()
}
const joint = (i: number): JogTarget => ({ kind: 'joint', index: i })
const tcp = (axis: TcpAxis): JogTarget => ({ kind: 'tcp', axis })

// Pads: segments 0 top, 1 right, 2 bottom, 3 left.
type Seg = { label: string; axis: TcpAxis; dir: 1 | -1 }
const XYZ: Seg[] = [
  { label: 'X+', axis: 'x', dir: 1 }, { label: 'Y−', axis: 'y', dir: -1 },
  { label: 'X−', axis: 'x', dir: -1 }, { label: 'Y+', axis: 'y', dir: 1 },
]
const RPY: Seg[] = [
  { label: 'P+', axis: 'pitch', dir: 1 }, { label: 'R+', axis: 'roll', dir: 1 },
  { label: 'P−', axis: 'pitch', dir: -1 }, { label: 'R−', axis: 'roll', dir: -1 },
]
const padActive = ref<Record<string, number>>({ xyz: -1, rpy: -1 })
const RING = 180
function padDown(e: PointerEvent, pad: 'xyz' | 'rpy') {
  const el = e.currentTarget as HTMLElement
  const r = el.getBoundingClientRect()
  const k = r.width / RING
  const seg = padSegment(e.clientX - r.left - r.width / 2, e.clientY - r.top - r.height / 2, 47 * k, 90 * k)
  if (seg < 0) return
  const s = (pad === 'xyz' ? XYZ : RPY)[seg]
  padActive.value[pad] = seg
  down(e, `${pad}${seg}`, tcp(s.axis), s.dir)
}
function padUp(pad: 'xyz' | 'rpy', cancelled = false) {
  const seg = padActive.value[pad]
  if (seg < 0) return
  padActive.value[pad] = -1
  if (cancelled) cancel(`${pad}${seg}`)
  else up(`${pad}${seg}`)
}
const segPos = ['t', 'r', 'b', 'l']

const busy = computed(() => !robot.sessionId)
onBeforeUnmount(() => motion.stop())
</script>

<template>
  <div class="mbar" data-test="motion-bar">
    <div class="hdr">
      <button class="chev" :class="{ closed: !open }" :aria-label="$t('motion.collapse')" @click="open = !open">⌄</button>
      <span class="lbl">{{ $t('motion.speed') }}</span>
      <el-slider v-model="motion.speed" class="speed" :min="1" :max="100" :show-tooltip="false" data-test="speed" />
      <span class="pctv num">{{ motion.speed }}%</span>
      <span class="gap" />
      <button class="btn" :disabled="busy" data-test="home" @click="motion.home()">{{ $t('motion.home') }}</button>
      <button class="btn" :disabled="busy" data-test="align" @click="motion.align()">{{ $t('motion.align') }}</button>
      <span class="flex" />
      <button class="btn stop" data-test="stop" @click="motion.stop()">STOP</button>
    </div>
    <div v-show="open" class="halves">
      <div class="half joints">
        <div v-for="(n, i) in robot.info?.joint_names ?? []" :key="n" class="jr">
          <label>J{{ i + 1 }}</label>
          <span class="lim num">{{ fmtLim(lim(i)[0]) }}</span>
          <el-slider
            :model-value="robot.q[i]"
            :min="lim(i)[0]"
            :max="lim(i)[1]"
            :step="0.1"
            :show-tooltip="false"
            class="jsl"
            :style="{ '--jc': COLORS[i % COLORS.length], '--jp': `${pct(i)}%` }"
            @input="(v: number | number[]) => robot.setJoint(i, Number(v))"
          />
          <span class="lim num">{{ fmtLim(lim(i)[1]) }}</span>
          <el-input-number
            :model-value="Number(robot.q[i]?.toFixed(1))"
            :controls="false"
            :precision="1"
            :min="lim(i)[0]"
            :max="lim(i)[1]"
            class="val"
            @change="(v: number | undefined) => robot.setJoint(i, Number(v ?? 0))"
          />
          <button
            v-for="d in [-1, 1] as const" :key="d" class="pill" :class="{ on: pressed === `j${i}${d}` }"
            :data-test="`j${i + 1}${d > 0 ? '+' : '-'}`"
            @pointerdown="down($event, `j${i}${d}`, joint(i), d)" @pointerup="up(`j${i}${d}`)"
            @pointercancel="cancel(`j${i}${d}`)" @lostpointercapture="up(`j${i}${d}`)"
          >
            {{ d > 0 ? '+' : '−' }}
          </button>
        </div>
      </div>
      <div class="half pads">
        <div v-for="pad in (['xyz', 'rpy'] as const)" :key="pad" class="padw">
          <div class="ab">
            <button
              v-for="d in [-1, 1] as const" :key="d" class="pill w" :class="{ on: pressed === `${pad}a${d}` }"
              :data-test="`${pad === 'xyz' ? 'z' : 'yaw'}${d > 0 ? '+' : '-'}`"
              @pointerdown="down($event, `${pad}a${d}`, tcp(pad === 'xyz' ? 'z' : 'yaw'), d)" @pointerup="up(`${pad}a${d}`)"
              @pointercancel="cancel(`${pad}a${d}`)" @lostpointercapture="up(`${pad}a${d}`)"
            >
              {{ pad === 'xyz' ? 'Z' : 'Yaw' }}{{ d > 0 ? '+' : '−' }}
            </button>
          </div>
          <div
            class="ring" :data-test="`pad-${pad}`"
            @pointerdown="padDown($event, pad)" @pointerup="padUp(pad)" @pointercancel="padUp(pad, true)" @lostpointercapture="padUp(pad)"
          >
            <div v-if="padActive[pad] >= 0" class="wedge" :style="{ '--rot': `${padActive[pad] * 90 - 45}deg` }" />
            <span
              v-for="(s, k) in (pad === 'xyz' ? XYZ : RPY)" :key="k" class="d" :class="[segPos[k], { act: padActive[pad] === k }]"
            >{{ s.label }}</span>
            <div class="ctr">{{ pad.toUpperCase() }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mbar { background: #1f2023; color: #e6e7ea; border-radius: 16px; padding: 0; box-sizing: border-box; user-select: none; font-size: 13px; }
.hdr { display: flex; align-items: center; gap: 10px; font-size: 12px; white-space: nowrap; padding: 0 16px; height: 69px; box-sizing: border-box; border-bottom: 1px solid #303136; }
.halves { display: flex; height: 299px; }
button { font: inherit; color: inherit; border: 0; cursor: pointer; }
button:disabled { opacity: .5; cursor: default; }
.chev { width: 26px; height: 26px; border-radius: 6px; background: #2a2b2f; display: grid; place-items: center; transition: transform .15s; }
.chev.closed { transform: rotate(180deg); }
.lbl { color: #9a9ca3; margin-left: 6px; }
.speed { width: 110px; --el-slider-main-bg-color: #3b6ef5; --el-slider-runway-bg-color: #3a3b40; --el-slider-height: 4px; --el-slider-button-size: 14px; }
.pctv { width: 36px; }
.gap { width: 14px; }
.flex { flex: 1; }
.btn { background: #2a2b2f; border-radius: 7px; padding: 10px 18px; font-size: 14px; }
.btn:hover:not(:disabled) { background: #34353a; }
.btn.stop { background: #e5383b; color: #fff; font-weight: 700; letter-spacing: 1px; padding: 10px 30px; font-size: 15px; box-shadow: 0 0 0 2px rgba(229, 56, 59, .35); }
.btn.stop:hover { background: #f04a4d; }
.half { flex: 1; min-width: 0; }
.half + .half { border-left: 1px solid #303136; }
.joints { flex: .95; display: flex; flex-direction: column; justify-content: space-evenly; padding: 6px 16px; }
.jr { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.jr label { width: 20px; font-weight: 600; }
.lim { width: 34px; font-size: 10px; color: #6f7177; text-align: center; font-family: inherit; }
.jsl { flex: 1; min-width: 60px; --el-slider-main-bg-color: var(--jc); --el-slider-runway-bg-color: #3a3b40; --el-slider-height: 5px; --el-slider-button-size: 15px; }
.jsl :deep(.el-slider__button) { border-color: var(--jc); border-width: 3px; }
.val { width: 60px !important; }
.val :deep(.el-input__wrapper) { background: #16171a; box-shadow: none; padding: 0 4px; }
.val :deep(.el-input__inner) { color: #e6e7ea; text-align: center; font-variant-numeric: tabular-nums; }
.pill { background: #2f3035; border-radius: 14px; padding: 5px 15px; font-size: 14px; text-align: center; touch-action: none; }
.pill:hover { background: #3a3b40; }
.pill.on { background: #3b6ef5; }
.pill.w { min-width: 84px; font-size: 13px; padding: 7px 0; }
.pads { display: flex; align-items: center; justify-content: space-evenly; padding: 18px 28px; }
.padw { display: flex; flex-direction: column; align-items: center; gap: 18px; }
.ab { display: flex; gap: 20px; }
.ring { position: relative; width: 180px; height: 180px; border-radius: 50%; touch-action: none; cursor: pointer;
  background: radial-gradient(circle, #1f2023 0 46px, #2f3035 47px 87px, #1f2023 88px); }
.wedge { position: absolute; inset: 0; border-radius: 50%; pointer-events: none;
  background: conic-gradient(from var(--rot), #3b6ef5 0 90deg, transparent 90deg);
  -webkit-mask: radial-gradient(circle, transparent 47px, #000 48px 87px, transparent 88px);
  mask: radial-gradient(circle, transparent 47px, #000 48px 87px, transparent 88px); }
.ctr { position: absolute; inset: 0; display: grid; place-items: center; font-weight: 700; font-size: 16px; pointer-events: none; }
.d { position: absolute; font-size: 14px; width: 40px; height: 26px; line-height: 26px; text-align: center; pointer-events: none; color: #c9cbd1; z-index: 1; }
.d.t { top: 10px; left: 70px; } .d.b { bottom: 10px; left: 70px; } .d.l { left: 6px; top: 77px; } .d.r { right: 6px; top: 77px; }
.d.act { color: #fff; font-weight: 700; }
</style>
