<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRobotStore } from '../stores/robot'
const robot = useRobotStore()
const mass = ref(robot.payload.mass_kg)
const com = ref<number[]>([...robot.payload.com_mm])
watch(
  () => robot.payload,
  (p) => {
    mass.value = p.mass_kg
    com.value = [...p.com_mm]
  },
)
</script>

<template>
  <div>
    <div class="panel-title">{{ $t('payload.title') }}</div>
    <el-form label-position="top" size="small">
      <el-form-item :label="$t('payload.mass')">
        <el-input-number v-model="mass" :min="0" :step="0.1" :precision="3" data-test="payload-mass" style="width: 100%" />
      </el-form-item>
      <el-form-item :label="$t('payload.com')">
        <div class="grid3">
          <el-input-number v-for="i in 3" :key="i" v-model="com[i - 1]" :controls="false" :precision="1" />
        </div>
      </el-form-item>
    </el-form>
    <div class="row">
      <span class="hint">{{ $t('payload.hint') }}</span>
      <el-button size="small" type="primary" plain @click="robot.applyPayload({ mass_kg: mass, com_mm: com })">
        {{ $t('payload.apply') }}
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; width: 100%; }
.grid3 :deep(.el-input-number) { width: 100%; }
.row { display: flex; justify-content: space-between; align-items: flex-start; gap: 6px; }
</style>
