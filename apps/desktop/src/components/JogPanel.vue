<script setup lang="ts">
import { ref } from 'vue'
import { useRobotStore } from '../stores/robot'
import { fmt } from '../lib/units'
import type { Pose6 } from '../rpc/types'
const robot = useRobotStore()
const target = ref<number[]>([830, 0, 200, -180, 0, 0])
const frame = ref<'tcp' | 'flange'>('tcp')
const labels = ['X', 'Y', 'Z', 'R', 'P', 'Y']
function lim(i: number): [number, number] {
  const l = robot.info?.limits_deg[i] ?? [-360, 360]
  return [Math.max(l[0], -360), Math.min(l[1], 360)]
}
function useCurrent() {
  const p = frame.value === 'tcp' ? robot.fk?.tcp_pose : robot.fk?.flange_pose
  if (p) target.value = p.map((v) => Number(v.toFixed(3)))
}
</script>

<template>
  <div>
    <div class="panel-title">{{ $t('jog.title') }}</div>
    <div v-for="(n, i) in robot.info?.joint_names ?? []" :key="n" class="joint">
      <span class="jn">J{{ i + 1 }}</span>
      <el-slider
        :model-value="robot.q[i]"
        :min="lim(i)[0]"
        :max="lim(i)[1]"
        :step="0.1"
        :show-tooltip="false"
        size="small"
        @input="(v: number | number[]) => robot.setJoint(i, Number(v))"
      />
      <el-input-number
        :model-value="robot.q[i]"
        size="small"
        :controls="false"
        :precision="3"
        class="num"
        @change="(v: number | undefined) => robot.setJoint(i, Number(v ?? 0))"
      />
    </div>
    <el-button size="small" text @click="robot.setQ(robot.info?.default_q_deg ?? [])">{{ $t('jog.home') }}</el-button>

    <div class="panel-title">{{ $t('jog.target') }}</div>
    <div class="grid6">
      <label v-for="(l, i) in labels" :key="i">
        <span>{{ l }}</span>
        <el-input-number v-model="target[i]" size="small" :controls="false" :precision="3" />
      </label>
    </div>
    <div class="row">
      <el-radio-group v-model="frame" size="small">
        <el-radio-button value="tcp">TCP</el-radio-button>
        <el-radio-button value="flange">Flange</el-radio-button>
      </el-radio-group>
      <el-button size="small" text @click="useCurrent">⤓</el-button>
      <el-button size="small" type="primary" :loading="robot.busy" data-test="solve-ik" @click="robot.checkPose(target as Pose6, frame)">
        {{ $t('jog.solve') }}
      </el-button>
    </div>
    <el-select
      v-if="robot.check"
      :model-value="robot.selectedSolution"
      size="small"
      style="width: 100%; margin-top: 6px"
      @update:model-value="robot.selectSolution"
    >
      <el-option
        v-for="(s, i) in robot.check.solutions"
        :key="i"
        :value="i"
        :label="`${$t('jog.solution')} ${i + 1}/${robot.check.solutions.length} · elbow ${s.branch.elbow} · wrist ${s.branch.wrist} · [${s.q_deg.map((v) => fmt(v, 1)).join(', ')}]`"
      />
    </el-select>
  </div>
</template>

<style scoped>
.joint { display: grid; grid-template-columns: 24px 1fr 78px; align-items: center; gap: 8px; }
.jn { color: #57606a; font-weight: 600; }
.joint :deep(.el-input-number) { width: 78px; }
.grid6 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px 6px; }
.grid6 label { display: flex; align-items: center; gap: 4px; }
.grid6 span { width: 12px; color: #57606a; }
.grid6 :deep(.el-input-number) { width: 100%; }
.row { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; }
</style>
