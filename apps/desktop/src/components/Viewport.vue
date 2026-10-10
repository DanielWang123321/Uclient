<script setup lang="ts">
import { markRaw, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { SceneController } from '../three/SceneController'
import { useRobotStore } from '../stores/robot'
const props = defineProps<{ insets?: { left: number; right: number; top: number; bottom: number } }>()
const robot = useRobotStore()
const host = ref<HTMLDivElement>()
const state = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')
const show = ref({ base: true, tcp: true, com: true })
let ctl: SceneController | null = null

function load() {
  if (!ctl || !robot.info) return
  state.value = 'loading'
  const ee = `link${robot.info.dof}`
  ctl.loadUrdf(robot.info.visual_urdf_relpath, ee)
}

onMounted(() => {
  ctl = markRaw(new SceneController(host.value!))
  ctl.onLoaded = (ok) => {
    state.value = ok ? 'ready' : 'error'
    if (ok && ctl && robot.info) {
      ctl.setJoints(robot.info.joint_names, robot.q)
      ctl.setTcp(robot.tcpOffset)
      ctl.setPayload(robot.payload.mass_kg, robot.payload.com_mm)
    }
  }
  if (props.insets) ctl.setInsets(props.insets)
  ;(window as unknown as { __ugclientScene?: SceneController }).__ugclientScene = ctl
  load()
})
onBeforeUnmount(() => {
  ctl?.dispose()
  ctl = null
})
watch(() => robot.info?.visual_urdf_relpath, load)
watch(() => props.insets, (i) => i && ctl?.setInsets(i), { deep: true })
watch(
  () => [...robot.q],
  (q) => robot.info && ctl?.setJoints(robot.info.joint_names, q),
)
watch(() => robot.tcpOffset, (o) => ctl?.setTcp(o))
watch(() => robot.payload, (p) => ctl?.setPayload(p.mass_kg, p.com_mm))
watch(show, (s) => {
  ctl?.setVisible('base', s.base)
  ctl?.setVisible('tcp', s.tcp)
  ctl?.setVisible('com', s.com && robot.payload.mass_kg > 0)
}, { deep: true })
</script>

<template>
  <div class="vp">
    <div ref="host" class="canvas" data-test="viewport"></div>
    <div class="toolbar" data-test="view-toolbar">
      <button :title="$t('view.reset')" @click="ctl?.resetView()">⟲</button>
      <span class="sep">|</span>
      <button v-for="k in (['base', 'tcp', 'com'] as const)" :key="k" :class="{ off: !show[k] }" :data-test="`view-${k}`" @click="show[k] = !show[k]">
        {{ $t(`view.${k}`) }}
      </button>
    </div>
    <div v-if="state === 'loading'" class="overlay">{{ $t('view.loading') }}</div>
    <div v-if="state === 'error'" class="overlay err">{{ $t('view.loadFailed') }}</div>
  </div>
</template>

<style scoped>
.vp { position: relative; width: 100%; height: 100%; min-height: 200px; }
.canvas { position: absolute; inset: 0; }
/* v8 mockup .toolbar */
.toolbar { position: absolute; left: 50%; transform: translateX(-50%); top: 16px; background: #1f2023; color: #e6e7ea;
  border-radius: 10px; padding: 10px 24px; display: flex; align-items: center; gap: 26px; font-size: 15px; line-height: 20px; }
.toolbar button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; font-size: 13px; }
.toolbar button:first-child { font-size: 15px; }
.toolbar button.off { color: #6f7177; text-decoration: line-through; }
.toolbar .sep { color: #888; }
.overlay { position: absolute; top: 64px; left: 50%; transform: translateX(-50%); color: #fff; background: rgba(0,0,0,.5); padding: 4px 10px; border-radius: 4px; }
.overlay.err { background: rgba(200,40,40,.8); }
</style>
