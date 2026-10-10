<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRobotStore } from '../stores/robot'
const robot = useRobotStore()
const labels = ['x', 'y', 'z', 'r', 'p', 'y']
const draft = ref<number[]>([...robot.tcpOffset])
watch(
  () => robot.tcpOffset,
  (v) => (draft.value = [...v]),
)
const { t } = useI18n()
const presets = computed(() => {
  const list = [{ name: t('tcp.flange'), offset: [0, 0, 0, 0, 0, 0] }]
  const info = robot.info
  if (info && info.end_effector !== 'none')
    list.push({ name: `${t(`ee.${info.end_effector}`)} (${t('tcp.toolDefault')})`, offset: [...info.default_tcp_offset] })
  return list
})
</script>

<template>
  <div>
    <div class="panel-title">{{ $t('tcp.title') }}</div>
    <el-select size="small" placeholder="Preset" style="width: 100%; margin-bottom: 6px" @change="(i: number) => (draft = [...presets[i].offset])">
      <el-option v-for="(p, i) in presets" :key="p.name" :label="p.name" :value="i" />
    </el-select>
    <div class="grid6">
      <label v-for="(l, i) in labels" :key="i">
        <span>{{ l }}</span>
        <el-input-number v-model="draft[i]" size="small" :controls="false" :precision="2" />
      </label>
    </div>
    <div class="row">
      <span class="hint">{{ $t('tcp.hint') }}</span>
      <el-button size="small" type="primary" plain @click="robot.applyTcp(draft)">{{ $t('tcp.apply') }}</el-button>
    </div>
  </div>
</template>

<style scoped>
.grid6 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px 6px; }
.grid6 label { display: flex; align-items: center; gap: 4px; }
.grid6 span { width: 10px; color: #57606a; }
.grid6 :deep(.el-input-number) { width: 100%; }
.row { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; gap: 6px; }
</style>
