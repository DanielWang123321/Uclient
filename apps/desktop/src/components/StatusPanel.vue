<script setup lang="ts">
import { useRobotStore } from '../stores/robot'
import { fmt } from '../lib/units'
const robot = useRobotStore()
</script>

<template>
  <div>
    <div class="panel-title">{{ $t('status.title') }}</div>
    <div class="kv"><span>{{ $t('status.tcp') }}</span><span class="num">{{ robot.fk?.tcp_pose.map((v) => fmt(v, 1)).join(', ') ?? '—' }}</span></div>
    <div class="kv"><span>{{ $t('status.flange') }}</span><span class="num">{{ robot.fk?.flange_pose.map((v) => fmt(v, 1)).join(', ') ?? '—' }}</span></div>
    <div v-if="robot.check" class="kv">
      <span>{{ $t('status.reachable') }}</span>
      <span>✔ {{ $t('status.solutions', { n: robot.check.solutions.length }) }}</span>
    </div>
    <div v-if="robot.lastError" class="err">{{ robot.lastError }}</div>
  </div>
</template>

<style scoped>
.kv { display: flex; justify-content: space-between; gap: 8px; padding: 2px 0; }
.kv span:first-child { color: #57606a; }
.err { color: var(--uc-high); font-size: 12px; margin-top: 4px; word-break: break-word; }
</style>
