<script setup lang="ts">
// Read-only robot state: simulated controller state, TCP pose and joint angles.
import { computed } from 'vue'
import { useRobotStore } from '../stores/robot'
import { useMotionStore } from '../stores/motion'
import { STATE } from '../lib/motion'
import { fmt } from '../lib/units'
const robot = useRobotStore()
const motion = useMotionStore()
const stateKey = computed(() =>
  motion.state === STATE.moving ? 'moving' : motion.state === STATE.stopped ? 'stopped' : 'ready',
)
const tcpLabels = ['X', 'Y', 'Z', 'Roll', 'Pitch', 'Yaw']
</script>

<template>
  <div data-test="info-panel">
    <div class="panel-title">{{ $t('info.state') }}</div>
    <div class="kv">
      <i>{{ $t('info.state') }}</i>
      <b :class="stateKey" data-test="sim-state">{{ $t(`info.${stateKey}`) }} ({{ motion.state }})</b>
      <i>{{ $t('info.payload') }}</i><b class="num">{{ fmt(robot.payload.mass_kg, 2) }} kg</b>
    </div>
    <div class="panel-title">{{ $t('info.tcp') }}</div>
    <div class="kv">
      <template v-for="k in [0, 3, 1, 4, 2, 5]" :key="k">
        <i>{{ tcpLabels[k] }}</i>
        <b class="num">{{ robot.fk ? `${fmt(robot.fk.tcp_pose[k], 1)}${k < 3 ? ' mm' : '°'}` : '—' }}</b>
      </template>
    </div>
    <div class="panel-title">{{ $t('info.joints') }}</div>
    <div class="kv">
      <template v-for="i in robot.q.map((_, i) => i)" :key="i">
        <i>J{{ i + 1 }}</i><b class="num" :data-test="`q${i + 1}`">{{ fmt(robot.q[i], 1) }}°</b>
      </template>
    </div>
  </div>
</template>

<style scoped>
.kv { display: grid; grid-template-columns: auto 1fr auto 1fr; gap: 6px 8px; font-size: 12px; }
.kv i { font-style: normal; color: #57606a; }
.kv b { font-weight: 500; }
.kv b.moving { color: var(--el-color-primary); }
.kv b.ready { color: var(--uc-ok); }
.kv b.stopped { color: var(--uc-warn); }
</style>
