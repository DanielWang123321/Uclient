<script setup lang="ts">
import { computed, onMounted, provide, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import enLocale from 'element-plus/es/locale/lang/en'
import CheckView from './views/CheckView.vue'
import { useEngineStore } from './stores/engine'
import { useRobotStore } from './stores/robot'

const { locale } = useI18n()
const engine = useEngineStore()
const robot = useRobotStore()
const elLocale = computed(() => (locale.value === 'zh' ? zhCn : enLocale))
watch(locale, (l) => localStorage.setItem('ugclient.locale', l))

async function start() {
  if (await engine.connect()) {
    await robot.fetchRobots()
    await robot.load('uf850')
  }
}
provide('engine.retry', start)
onMounted(start)
</script>

<template>
  <el-config-provider :locale="elLocale" size="small">
    <!-- v8 layout: the Check page fills the window. Trajectory / Workspace tabs return once they have content. -->
    <CheckView />
  </el-config-provider>
</template>
