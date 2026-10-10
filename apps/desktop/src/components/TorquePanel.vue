<script setup lang="ts">
import { computed } from 'vue'
import { useRobotStore } from '../stores/robot'
import { fmt, fmtPct, utilLevel } from '../lib/units'
import { torqueCsv } from '../lib/csv'
import { saveText } from '../lib/files'
const robot = useRobotStore()
const rows = computed(() => {
  const t = robot.torque
  if (!t || !robot.info) return []
  return robot.info.joint_names.map((n, i) => ({
    j: `J${i + 1}`,
    tau: t.tau_nm[i],
    arm: t.tau_arm_nm?.[i],
    pl: t.tau_payload_nm?.[i],
    max: t.effort_limits_nm[i],
    util: t.utilization[i],
    level: utilLevel(t.utilization[i]),
  }))
})
async function exportCsv() {
  if (!robot.torque || !robot.info) return
  await saveText(`${robot.key}_torque.csv`, torqueCsv(robot.info.joint_names, robot.q, robot.torque))
}
</script>

<template>
  <div>
    <div class="panel-title">{{ $t('torque.title') }}</div>
    <table class="tq num" data-test="torque-table">
      <thead>
        <tr>
          <th></th><th>{{ $t('torque.total') }}</th><th>{{ $t('torque.arm') }}</th><th>{{ $t('torque.payload') }}</th><th :title="$t('torque.max')">{{ $t('torque.pct') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.j" :class="r.level">
          <td>{{ r.j }}</td>
          <td :data-test="`tau-${r.j}`">{{ fmt(r.tau, 3) }}</td>
          <td>{{ fmt(r.arm, 2) }}</td>
          <td>{{ fmt(r.pl, 2) }}</td>
          <td>
            <div class="bar"><div :style="{ width: `${Math.min(Math.abs(r.util) * 100, 100)}%` }"></div></div>
            {{ fmtPct(r.util) }}
          </td>
        </tr>
      </tbody>
    </table>
    <div class="row">
      <span class="hint">{{ $t('torque.assumption') }}</span>
      <el-button size="small" :disabled="!robot.torque" @click="exportCsv">{{ $t('torque.exportCsv') }}</el-button>
    </div>
  </div>
</template>

<style scoped>
.tq { width: 100%; border-collapse: collapse; font-size: 12px; }
.tq th { text-align: right; color: #57606a; font-weight: 500; padding: 2px 4px; }
.tq td { text-align: right; padding: 3px 4px; border-top: 1px solid #eef0f3; }
.tq td:first-child { text-align: left; font-weight: 600; }
.bar { display: inline-block; width: 40px; height: 6px; background: #eef0f3; border-radius: 3px; vertical-align: middle; margin-right: 4px; }
.bar div { height: 100%; border-radius: 3px; background: var(--uc-ok); }
tr.warn .bar div { background: var(--uc-warn); }
tr.high .bar div, tr.over .bar div { background: var(--uc-high); }
tr.over td { color: var(--uc-high); font-weight: 600; }
.row { display: flex; justify-content: space-between; align-items: flex-start; gap: 6px; margin-top: 6px; }
</style>
