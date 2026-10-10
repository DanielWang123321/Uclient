<script setup lang="ts">
import { computed, onMounted, provide, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import enLocale from 'element-plus/es/locale/lang/en'
import CheckView from './views/CheckView.vue'
import { useEngineStore } from './stores/engine'
import { useRobotStore } from './stores/robot'
import { useSettingsStore } from './stores/settings'

const { locale } = useI18n()
const engine = useEngineStore()
const robot = useRobotStore()
const settings = useSettingsStore()
const elLocale = computed(() => (locale.value === 'zh' ? zhCn : enLocale))
watch(locale, (l) => localStorage.setItem('ugclient.locale', l))

async function start() {
  if (await engine.connect()) {
    await robot.fetchRobots()
    const known = (k: string) => robot.robots.some((r) => r.key === k)
    const last = settings.restoreSession ? settings.session : null
    if (last && known(last.robot) && (await robot.select(last.robot, last.endEffector))) {
      await robot.applyTcp(last.tcpOffset)
      await robot.applyPayload(last.payload)
      if (last.q.length === robot.info?.dof) await robot.setQ(last.q)
    } else {
      await robot.load(known(settings.defaultRobot) ? settings.defaultRobot : 'uf850')
    }
  }
}

// Remember the session (robot, tool, TCP, payload, joints) for "restore last session".
let saveTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => [robot.key, robot.endEffector, robot.tcpOffset, robot.payload, robot.q, settings.restoreSession],
  () => {
    if (!robot.info) return
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      settings.session = settings.restoreSession
        ? { robot: robot.key, endEffector: robot.endEffector, tcpOffset: [...robot.tcpOffset], payload: { ...robot.payload, com_mm: [...robot.payload.com_mm] }, q: [...robot.q] }
        : null
    }, 500)
  },
  { deep: true },
)
provide('engine.retry', start)
onMounted(start)
</script>

<template>
  <el-config-provider :locale="elLocale" size="small">
    <!-- v8 layout: the Check page fills the window. Trajectory / Workspace tabs return once they have content. -->
    <CheckView />
  </el-config-provider>
</template>
